import base64, json, os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.crochet_engine import Gauge, ShapeGraph, dinosaur_shape_graph, fit_graph_to_image, estimate_depth_pose
from app.crochet_engine.quality import assess_graph, construction_notes
from app.crochet_engine.complexity import analyze_complexity
from app.crochet_engine.design_model import DESIGN_SCHEMA, DESIGN_SYSTEM_PROMPT, fallback_design, generate_concept_image
from app.crochet_engine.pipeline import compile_design
from app.config import get_api_key, set_api_key

APP_DIR=Path(__file__).resolve().parent; STATIC=APP_DIR/'static'
app=FastAPI(title='Amigurumi AI Designer — v0.7.3')

VEC={"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"},"z":{"type":"number"}},"required":["x","y","z"],"additionalProperties":False}
ROT={"type":"object","properties":{"rx":{"type":"number"},"ry":{"type":"number"},"rz":{"type":"number"}},"required":["rx","ry","rz"],"additionalProperties":False}
SPAN={"type":["object","null"],"properties":{"width":{"type":"number"},"height":{"type":"number"}},"required":["width","height"],"additionalProperties":False}
ANCHOR={"type":["object","null"],"properties":{"x":{"type":"number"},"y":{"type":"number"}},"required":["x","y"],"additionalProperties":False}
META={"type":"object","properties":{"source":{"type":"string"},"confidence":{"type":"number"},"units":{"type":"string"},"image_anchor_px":ANCHOR,"image_span_px":SPAN,"depth_hint":{"type":["string","null"]}},"required":["source","confidence","units","image_anchor_px","image_span_px","depth_hint"],"additionalProperties":False}
CP={"type":"object","properties":{"name":{"type":"string"},"position":VEC,"radius_cm":{"type":"number"},"role":{"type":"string"}},"required":["name","position","radius_cm","role"],"additionalProperties":False}
NODE={"type":"object","properties":{"id":{"type":"string"},"name":{"type":"string"},"kind":{"type":"string"},"primitive":{"type":"string"},"position":VEC,"rotation":ROT,"scale":VEC,"profile":{"type":"array","items":{"type":"object","properties":{"z_cm":{"type":"number"},"diameter_cm":{"type":"number"}},"required":["z_cm","diameter_cm"],"additionalProperties":False}},"start_stitches":{"type":"integer"},"material":{"type":"string"},"symmetry_group":{"type":["string","null"]},"required":{"type":"boolean"},"metadata":META,"connections":{"type":"array","items":CP}},"required":["id","name","kind","primitive","position","rotation","scale","profile","start_stitches","material","symmetry_group","required","metadata","connections"],"additionalProperties":False}
EDGE={"type":"object","properties":{"id":{"type":"string"},"parent":{"type":"string"},"parent_point":{"type":"string"},"child":{"type":"string"},"child_point":{"type":"string"},"joint":{"type":"string"},"seam_cm":{"type":"number"},"notes":{"type":"string"}},"required":["id","parent","parent_point","child","child_point","joint","seam_cm","notes"],"additionalProperties":False}
VISION_PART={"type":"object","properties":{"id":{"type":"string"},"label":{"type":"string"},"category":{"type":"string"},"role":{"type":"string"},"visible":{"type":"boolean"},"confidence":{"type":"number"},"parent_id":{"type":["string","null"]},"symmetry_group":{"type":["string","null"]},"image_anchor_px":ANCHOR,"image_span_px":SPAN,"notes":{"type":"string"}},"required":["id","label","category","role","visible","confidence","parent_id","symmetry_group","image_anchor_px","image_span_px","notes"],"additionalProperties":False}
SCHEMA={"type":"object","properties":{
"subject":{"type":"string"},"style_notes":{"type":"string"},"palette":{"type":"array","items":{"type":"string"}},"parts":{"type":"array","items":{"type":"string"}},
"vision_parts":{"type":"array","items":VISION_PART},
"dimensions":{"type":"object","properties":{"height_cm":{"type":"number"},"width_cm":{"type":"number"},"depth_cm":{"type":"number"}},"required":["height_cm","width_cm","depth_cm"],"additionalProperties":False},
"shape_graph":{"type":"object","properties":{"version":{"type":"string"},"name":{"type":"string"},"metadata":META,"nodes":{"type":"array","items":NODE},"edges":{"type":"array","items":EDGE}},"required":["version","name","metadata","nodes","edges"],"additionalProperties":False},
"depth_pose":{"type":"object","properties":{"status":{"type":"string"},"confidence":{"type":"number"},"notes":{"type":"string"}},"required":["status","confidence","notes"],"additionalProperties":False},
"pattern":{"type":"string"},"assembly":{"type":"string"},"checks":{"type":"array","items":{"type":"string"}}},
"required":["subject","style_notes","palette","parts","vision_parts","dimensions","shape_graph","depth_pose","pattern","assembly","checks"],"additionalProperties":False}

DECOMPOSE_SCHEMA={"type":"object","properties":{"subject":{"type":"string"},"overall_confidence":{"type":"number"},"parts":{"type":"array","items":VISION_PART},"notes":{"type":"string"}},"required":["subject","overall_confidence","parts","notes"],"additionalProperties":False}

DECOMPOSE_PROMPT='''Sei il modulo di SCOMPOSIZIONE VISIVA di Amigurumi AI. Trasforma foto e/o descrizione in una lista di parti costruttive osservabili prima della geometria. Non generare pattern e non inventare parti nascoste. Ogni parte deve avere id stabile, label, category (primary|limb|appendage|detail|decorative|other), role (body|head|neck|muzzle|tail|leg|arm|ear|horn|wing|eye|plate|detail|other), visibilità, confidence, eventuale parent_id e symmetry_group. image_anchor_px e image_span_px vanno compilati solo se osservabili nella foto, altrimenti null. Raggruppa elementi ripetuti con lo stesso symmetry_group. Se un dettaglio è ambiguo, abbassa confidence e spiega il motivo nelle notes.'''

SYSTEM_PROMPT='''Sei il modulo di VISIONE SEMANTICA di Amigurumi AI. Non scrivere un pattern creativo: ricostruisci il soggetto in parti e proporzioni utili a un motore deterministico. FOTO/TESTO -> PARTI VISIVE -> SHAPE GRAPH -> MOTORE CROCHET.
Usa cm. Ogni pezzo lavorabile ha almeno 2 punti profile, z crescente, diametro positivo. connections è un ARRAY di oggetti con name/position/radius_cm/role; il server lo normalizza internamente. metadata DEVE contenere source, confidence, units, image_anchor_px, image_span_px, depth_hint, tutti presenti anche se null. Tutte le parti devono essere realmente osservabili o marcate con bassa confidence. Non inventare dettagli invisibili come certi. Usa symmetry_group per elementi ripetuti. Il campo vision_parts deve elencare la decomposizione semantica prima della geometria. Ogni vision_part include category, role, parent_id, symmetry_group e anchor/span quando osservabili. pattern/assembly sono segnaposto: il server li sostituisce con output deterministico.
'''

def _meta(source='ai_vision',confidence=.5,anchor=None,span=None,depth=None):
    return {'source':source,'confidence':float(confidence),'units':'cm','image_anchor_px':anchor,'image_span_px':span,'depth_hint':depth}

def normalize_graph(raw):
    data=dict(raw or {}); data['metadata']=dict(data.get('metadata') or {})
    data['metadata'].setdefault('source','ai_vision'); data['metadata'].setdefault('confidence',.5); data['metadata'].setdefault('units','cm'); data['metadata'].setdefault('image_anchor_px',None); data['metadata'].setdefault('image_span_px',None); data['metadata'].setdefault('depth_hint',None)
    nodes=[]
    for n in data.get('nodes',[]):
        n=dict(n); m=dict(n.get('metadata') or {})
        for k,v in _meta().items(): m.setdefault(k,v)
        n['metadata']=m
        conns=n.get('connections',[])
        if isinstance(conns,dict): conns=[dict(v, name=k) for k,v in conns.items()]
        n['connections']=conns
        nodes.append(n)
    data['nodes']=nodes; return data

def fallback(desc,height,hook):
    graph=dinosaur_shape_graph(scale=max(height/15.0,.35))
    for n in graph.nodes.values(): n.metadata.update(_meta('fallback',.45))
    return {'subject':desc or 'soggetto dalla foto','style_notes':'Fallback parametrico; senza API key non è analisi visuale reale.','palette':['verde oliva','verde scuro','nero'],'parts':[n.name for n in graph.nodes.values() if n.kind!='detail'],'vision_parts':[{'id':n.id,'label':n.name,'category':'detail' if n.kind=='detail' else ('limb' if 'leg' in n.id else 'primary'),'role':('leg' if 'leg' in n.id else ('body' if n.id=='body' else ('head' if n.id=='head' else 'other'))),'visible':True,'confidence':.45,'parent_id':None,'symmetry_group':n.symmetry_group,'image_anchor_px':None,'image_span_px':None,'notes':'fallback'} for n in graph.nodes.values()], 'dimensions':{'height_cm':height,'width_cm':round(height*.75,1),'depth_cm':round(height*.55,1)},'shape_graph':graph.to_dict(),'depth_pose':{'status':'fallback','confidence':.2,'notes':'Stima non visuale.'},'pattern':'','assembly':'','checks':[]}

def compile_graph(result,height_cm,hook_mm,image_bytes=None,stitches10=None,rounds10=None):
    raw=normalize_graph(result.get('shape_graph') or {}); graph=ShapeGraph.from_dict(raw); validation=graph.validate()
    image=None
    if image_bytes:
        try:
            import numpy as np, cv2
            image=cv2.imdecode(np.frombuffer(image_bytes,dtype=np.uint8),cv2.IMREAD_COLOR)
        except Exception as e: result.setdefault('checks',[]).append(f'ATTENZIONE: immagine non decodificata: {str(e)[:160]}')
    try:
        result['complexity']=analyze_complexity(image, result.get('subject','')).to_dict()
    except Exception as e:
        result.setdefault('checks',[]).append(f'ATTENZIONE: Complexity Analyzer: {str(e)[:180]}')
    if image is not None:
        try: result['profile_fit']=fit_graph_to_image(graph,image,height_cm).to_dict()
        except Exception as e: result.setdefault('checks',[]).append(f'ATTENZIONE: Profile Fit: {str(e)[:180]}')
        try: result['depth_pose']=estimate_depth_pose(graph,image,height_cm).to_dict()
        except Exception as e: result.setdefault('checks',[]).append(f'ATTENZIONE: Depth/Pose: {str(e)[:180]}')
    spc=float(stitches10 or max(18,min(40,28*(2.5/max(hook_mm,.5)))))
    rpc=float(rounds10 or max(20,min(45,32*(2.5/max(hook_mm,.5)))))
    gauge=Gauge(spc,rpc); project=graph.compile(gauge,include_details=True)
    quality=assess_graph(graph,project,height_cm)
    result['shape_graph']=graph.to_dict(); result['parts']=[n.name for n in graph.nodes.values() if n.kind!='detail']
    result['pattern']=project.pattern; result['assembly']='\n'.join(project.assembly+construction_notes(graph)); result['checks']=project.checks+[f'Gauge: {spc:.1f} maglie/10 cm; {rpc:.1f} giri/10 cm.']
    result['checks'] += [f'QUALITY {quality.status}: {quality.score:.0f}/100'] + [f'ATTENZIONE: {w}' for w in quality.warnings]
    result['quality']=quality.to_dict(); result['_graph_validation']={'ok':validation.ok,'errors':validation.errors,'warnings':validation.warnings,'node_count':len(graph.nodes),'edge_count':len(graph.edges),'pattern_part_count':len(project.parts)}
    return result

@app.get('/')
def home(): return FileResponse(STATIC/'index.html')

def _decode_image_bytes(img_bytes):
    if not img_bytes:
        return None
    try:
        import numpy as np, cv2
        return cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None

def _heuristic_decomposition(description: str, image=None):
    text=(description or '').lower()
    common=[('body','corpo','primary','body'),('head','testa','primary','head'),('neck','collo','primary','neck'),('muzzle','muso','appendage','muzzle'),('tail','coda','appendage','tail'),('leg','zampa','limb','leg'),('arm','braccio','limb','arm'),('ear','orecchio','appendage','ear'),('horn','corno','appendage','horn'),('wing','ala','appendage','wing'),('eye','occhio','detail','eye')]
    parts=[]
    for pid,label,cat,role in common:
        present=label in text or (pid=='body' and not parts)
        if not present: continue
        count=2 if pid in {'leg','ear','eye'} else 1
        for i in range(count):
            parts.append({'id':f'{pid}{i+1}' if count>1 else pid,'label':label+(f' {i+1}' if count>1 else ''),'category':cat,'role':role,'visible':True,'confidence':.45,'parent_id':None,'symmetry_group':pid if count>1 else None,'image_anchor_px':None,'image_span_px':None,'notes':'Decomposizione euristica; da confermare con analisi visiva AI.'})
    if not parts:
        parts=[{'id':'body','label':'corpo/soggetto principale','category':'primary','role':'body','visible':True,'confidence':.25,'parent_id':None,'symmetry_group':None,'image_anchor_px':None,'image_span_px':None,'notes':'Nessuna parte esplicita riconosciuta dal testo.'}]
    return {'subject':description or 'soggetto dalla foto','overall_confidence':.3 if image is None else .4,'parts':parts,'notes':'Modalità locale: decomposizione provvisoria.'}

@app.post('/api/decompose')
async def decompose(description:str=Form(''), image:Optional[UploadFile]=File(None)):
    img=await image.read() if image else None
    key=get_api_key()
    if not key:
        return JSONResponse({'mode':'fallback','result':_heuristic_decomposition(description,_decode_image_bytes(img))})
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        content=[{'type':'input_text','text':f'Descrizione: {description or "nessuna"}\nScomponi il soggetto in parti costruttive osservabili. Prima parti principali, poi appendici, poi dettagli. Non generare geometria o pattern.'}]
        if img:
            mime=image.content_type or 'image/png'
            content.append({'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(img).decode()}'})
        resp=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),input=[{'role':'system','content':DECOMPOSE_PROMPT},{'role':'user','content':content}],text={'format':{'type':'json_schema','name':'amigurumi_decomposition','strict':True,'schema':DECOMPOSE_SCHEMA}})
        raw=getattr(resp,'output_text',None)
        if not raw: raise RuntimeError('Nessun output di decomposizione ricevuto.')
        return JSONResponse({'mode':'ai','result':json.loads(raw)})
    except Exception as e:
        return JSONResponse({'mode':'fallback','warning':str(e)[:700],'result':_heuristic_decomposition(description,_decode_image_bytes(img))})

@app.post('/api/design')
async def design_model(description:str=Form(''), height_cm:float=Form(15), style:str=Form('fedele alla foto'), image:Optional[UploadFile]=File(None)):
    """Build the structured Design Model and optional amigurumi concept image."""
    img=await image.read() if image else None
    key=get_api_key()
    if not key:
        return JSONResponse({'mode':'fallback','result':fallback_design(description,height_cm,style),'concept_image':None,
                             'warning':'Nessuna API key: template locale provvisorio; concept image non generata.'})
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        text=(f"Descrizione: {description or 'nessuna'}\nTarget altezza: {height_cm} cm\nStile desiderato: {style}\n"
              "Costruisci l'AMIGURUMI DESIGN MODEL secondo lo schema. Identifica il soggetto prima della geometria e prepara quattro viste tecniche: frontale, posteriore, sinistra, destra. Non scrivere pattern.")
        content=[{'type':'input_text','text':text}]
        if img:
            mime=image.content_type or 'image/png'
            content.append({'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(img).decode()}'})
        resp=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),input=[
            {'role':'system','content':DESIGN_SYSTEM_PROMPT},{'role':'user','content':content}
        ],text={'format':{'type':'json_schema','name':'amigurumi_design_model','strict':True,'schema':DESIGN_SCHEMA}})
        raw=getattr(resp,'output_text',None)
        if not raw: raise RuntimeError('Nessun Design Model ricevuto.')
        design=json.loads(raw)
        concept_image=None; concept_warning=None
        try:
            concept_image=generate_concept_image(client,design,description,height_cm,style)
        except Exception as image_exc:
            concept_warning=f'Concept image non generata: {str(image_exc)[:500]}'
        return JSONResponse({'mode':'ai','result':design,'concept_image':concept_image,'warning':concept_warning})
    except Exception as e:
        return JSONResponse({'mode':'fallback','warning':str(e)[:700], 'result':fallback_design(description,height_cm,style), 'concept_image':None})

def _identity_gate(description: str, design: dict) -> dict:
    import re
    desc=(description or '').lower().strip()
    subject=str(design.get('subject') or '').lower().strip()
    summary=str(design.get('semantic_summary') or '').lower().strip()
    features=[str(x).lower() for x in (design.get('distinctive_features') or [])]
    confidence=float(design.get('overall_confidence') or 0)
    text=' '.join([subject, summary, ' '.join(features)])
    aliases={
      'orsetto':{'orso','orsetto','bear','teddy'}, 'teddy bear':{'orso','orsetto','bear','teddy'}, 'orso':{'orso','orsetto','bear','teddy'},
      'canguro':{'canguro','kangaroo'}, 'kangaroo':{'canguro','kangaroo'}, 'dinosauro':{'dinosauro','dinosaur'}, 'dinosaur':{'dinosauro','dinosaur'},
      'castoro':{'castoro','beaver'}, 'beaver':{'castoro','beaver'}, 'toro':{'toro','bull'}, 'bull':{'toro','bull'},
    }
    def toks(x): return set(re.findall(r"[a-zàèéìòù]+",x))
    dt=toks(desc); tt=toks(text); anchor=set()
    for k,vals in aliases.items():
        if k in desc or k in dt: anchor |= vals
    matched=bool(anchor & tt) if anchor else bool(dt & toks(subject))
    generic=subject in {'','soggetto amigurumi','soggetto dalla foto','soggetto'}
    ok=(not generic and confidence >= .65 and matched and bool(features))
    reasons=[]
    if generic: reasons.append('soggetto generico o mancante')
    if confidence < .65: reasons.append(f'confidenza identità {confidence:.2f} < 0.65')
    if not matched: reasons.append('soggetto semanticamente non coerente con la richiesta')
    if not features: reasons.append('nessuna caratteristica distintiva esplicita')
    return {'ok':ok,'confidence':confidence,'subject':design.get('subject',''),'matched':matched,'distinctive_feature_count':len(features),'reasons':reasons}

@app.post('/api/generate')
async def generate_amigurumi(description:str=Form(''),height_cm:float=Form(15),hook_mm:float=Form(2.5),level:str=Form('intermedio'),style:str=Form('fedele alla foto'),stitches10:float=Form(0),rounds10:float=Form(0),image:Optional[UploadFile]=File(None)):
    """Core end-to-end pipeline: semantic Design Model -> deterministic compilation."""
    img=await image.read() if image else None
    key=get_api_key()
    try:
        if not key:
            design=fallback_design(description,height_cm,style)
            compiled=compile_design(design,height_cm,hook_mm,stitches10 or None,rounds10 or None, _decode_image_bytes(img))
            graph=ShapeGraph.from_dict(compiled['shape_graph']); project=graph.compile(Gauge(stitches10 or 28,rounds10 or 32),include_details=True)
            quality=assess_graph(graph,project,height_cm).to_dict()
            return JSONResponse({'mode':'fallback','stage':'compiled','result':{**design,**compiled,'quality':quality,
                'identity_gate':{'ok':False,'reasons':['Nessuna API key: identità non verificata.']},
                'pipeline_gates':{'identity':False,'design_model':True,'shape_graph':compiled['graph_validation']['ok'],'geometry':True,'technique':True,'pattern':True,'validation':quality['status']!='FAIL'},
                'pipeline_status':'REVIEW','warning':'Nessuna API key: il modello semantico è locale/provvisorio.'}})
        from openai import OpenAI
        client=OpenAI(api_key=key)
        text=(f"Descrizione: {description or 'nessuna'}\nTarget: {height_cm} cm\nUncinetto: {hook_mm} mm\n"
              f"Livello: {level}; stile: {style}.\nAnalizza il soggetto e crea SOLO l'AMIGURUMI DESIGN MODEL strutturato. "
              "Identifica con particolare attenzione l'identità del soggetto e le caratteristiche distintive prima delle parti. "
              "Non generare pattern e non generare Shape Graph.")
        content=[{'type':'input_text','text':text}]
        if img:
            mime=image.content_type or 'image/png'
            content.append({'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(img).decode()}'})
        resp=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),input=[{'role':'system','content':DESIGN_SYSTEM_PROMPT},{'role':'user','content':content}],text={'format':{'type':'json_schema','name':'amigurumi_design_model','strict':True,'schema':DESIGN_SCHEMA}})
        raw=getattr(resp,'output_text',None)
        if not raw: raise RuntimeError('Nessun Design Model strutturato ricevuto.')
        design=json.loads(raw)
        compiled=compile_design(design,height_cm,hook_mm,stitches10 or None,rounds10 or None, _decode_image_bytes(img))
        identity=_identity_gate(description,design)
        graph=ShapeGraph.from_dict(compiled['shape_graph']); project=graph.compile(Gauge(stitches10 or 28,rounds10 or 32),include_details=True)
        quality=assess_graph(graph,project,height_cm).to_dict()
        gates={'identity':identity['ok'],'design_model':bool(design.get('subject')) and bool(design.get('parts')),'shape_graph':compiled['graph_validation']['ok'],'geometry':bool(compiled['pattern']),'technique':bool(compiled['techniques']),'pattern':bool(compiled['pattern']),'validation':quality['status']!='FAIL'}
        result={**design,**compiled,'quality':quality,'identity_gate':identity,'pipeline_gates':gates,'pipeline_status':'PASS' if all(gates.values()) else 'REVIEW'}
        if not identity['ok']: result['checks'].append('REVIEW: identità semantica non sufficientemente verificata; non considerare il pattern definitivo.')
        return JSONResponse({'mode':'ai','stage':'compiled','result':result})
    except Exception as e:
        return JSONResponse({'mode':'error','stage':'failed','error':str(e)[:1000]},status_code=500)

@app.post('/api/complexity')
async def complexity(description:str=Form(''), image:Optional[UploadFile]=File(None)):
    """Analyze construction complexity and always return a JSON response.

    The endpoint deliberately converts unexpected failures into a structured
    JSON error so the desktop UI never tries to parse FastAPI's plain-text
    "Internal Server Error" response as JSON.
    """
    try:
        img=await image.read() if image else None
        arr=None
        if img:
            try:
                import numpy as np, cv2
                arr=cv2.imdecode(np.frombuffer(img,dtype=np.uint8),cv2.IMREAD_COLOR)
                if arr is None:
                    return JSONResponse({'mode':'error','error':'Immagine non valida o non decodificabile.'}, status_code=400)
            except Exception as exc:
                return JSONResponse({'mode':'error','error':f"Impossibile leggere l'immagine: {str(exc)[:300]}"}, status_code=400)
        report=analyze_complexity(arr,description)
        return JSONResponse({'mode':'ok','result':report.to_dict()})
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JSONResponse({'mode':'error','error':f'Errore interno Complexity Analyzer: {str(exc)[:500]}'}, status_code=500)

@app.post('/api/analyze')
async def analyze(description:str=Form(''),height_cm:float=Form(15),hook_mm:float=Form(2.5),level:str=Form('intermedio'),style:str=Form('fedele alla foto'),stitches10:float=Form(0),rounds10:float=Form(0),design_json:str=Form(''),image:Optional[UploadFile]=File(None)):
    img=await image.read() if image else None; key=get_api_key()
    if not key: return JSONResponse({'mode':'fallback','result':compile_graph(fallback(description,height_cm,hook_mm),height_cm,hook_mm,img,stitches10 or None,rounds10 or None)})
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        content=[{'type':'input_text','text':f'''Descrizione: {description or "nessuna"}\nTarget: {height_cm} cm\nUncinetto: {hook_mm} mm\nGauge fornito: {stitches10 or "auto"} maglie/10cm, {rounds10 or "auto"} giri/10cm\nLivello: {level}; stile: {style}.\nAnalizza l'immagine se presente. Prima identifica le parti visibili in vision_parts, poi costruisci il Shape Graph coerente. Mantieni confidenza e anchor solo quando osservabili.\n\nAMIGURUMI DESIGN MODEL (se presente, usalo come rappresentazione intermedia autorevole per identità, parti, posa e relazioni; non sostituirlo con la sola silhouette):\n{design_json or "nessuno"}''' }]
        if img:
            mime=image.content_type or 'image/png'; content.append({'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(img).decode()}'})
        resp=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),input=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':content}],text={'format':{'type':'json_schema','name':'amigurumi_project','strict':True,'schema':SCHEMA}})
        raw=getattr(resp,'output_text',None)
        if not raw: raise RuntimeError('Nessun output strutturato ricevuto.')
        parsed=json.loads(raw)
        if design_json:
            try: parsed['design_model']=json.loads(design_json)
            except Exception: parsed['design_model']={'raw':design_json[:4000]}
        if not parsed.get('vision_parts'):
            parsed['vision_parts']=_heuristic_decomposition(description,_decode_image_bytes(img))['parts']
        return JSONResponse({'mode':'ai','result':compile_graph(parsed,height_cm,hook_mm,img,stitches10 or None,rounds10 or None)})
    except Exception as e:
        fb=compile_graph(fallback(description,height_cm,hook_mm),height_cm,hook_mm,img,stitches10 or None,rounds10 or None)
        if design_json:
            try: fb['design_model']=json.loads(design_json)
            except Exception: pass
        return JSONResponse({'mode':'fallback','warning':str(e)[:700],'result':fb})

@app.get('/api/settings')
def settings(): return {'has_openai_key':bool(get_api_key()),'model':os.getenv('OPENAI_MODEL','gpt-5.6-luna')}
@app.post('/api/settings')
async def update_settings(openai_api_key:str=Form('')): set_api_key(openai_api_key); return {'ok':True,'has_openai_key':bool(get_api_key()),'model':os.getenv('OPENAI_MODEL','gpt-5.6-luna')}
@app.get('/api/health')
def health(): return {'ok':True,'service':'amigurumi-ai','version':'0.7.3'}

@app.get('/api/update')
def update_status():
    return getattr(app.state, 'update_info', {'available': False, 'version': '0.7.3'})
app.mount('/static',StaticFiles(directory=STATIC),name='static')
