from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import math, re

@dataclass
class ComplexityReport:
    score: float
    level: str
    confidence: float
    reasons: list[str]
    metrics: Dict[str, float]
    recommendations: list[str]

    def to_dict(self):
        return asdict(self)

class ComplexityAnalyzer:
    """Pre-generation complexity estimator.

    It deliberately estimates *construction complexity*, not artistic beauty.
    With an image it uses coarse silhouette/edge statistics; with text only it
    uses lexical/semantic cues. It never pretends to recover hidden geometry.
    """
    def analyze(self, image=None, description: str = "") -> ComplexityReport:
        metrics = {
            'foreground_ratio': 0.0, 'aspect_ratio': 0.0, 'edge_density': 0.0,
            'component_count': 0.0, 'hole_count': 0.0, 'contour_complexity': 0.0,
            'symmetry_score': 0.0, 'text_detail_score': 0.0
        }
        reasons=[]; recommendations=[]; evidence=0.0
        if image is not None:
            try:
                import cv2, numpy as np
                gray=cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                h,w=gray.shape[:2]
                scale=min(1.0, 720.0/max(h,w))
                if scale<1:
                    gray=cv2.resize(gray,(max(1,int(w*scale)),max(1,int(h*scale))),interpolation=cv2.INTER_AREA)
                h,w=gray.shape[:2]
                # GrabCut with a safe central rectangle; fallback to Otsu/edges.
                mask=np.zeros((h,w),np.uint8)
                rect=(max(1,int(w*.03)),max(1,int(h*.03)),max(2,int(w*.94)),max(2,int(h*.94)))
                try:
                    bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
                    cv2.grabCut(cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR),mask,rect,bgd,fgd,3,cv2.GC_INIT_WITH_RECT)
                    fg=((mask==2)|(mask==3)).astype(np.uint8)*255
                except Exception:
                    _,fg=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                # Keep the largest plausible foreground component.
                n, labels, stats, _=cv2.connectedComponentsWithStats((fg>0).astype(np.uint8),8)
                if n>1:
                    areas=stats[1:,cv2.CC_STAT_AREA]; idx=1+int(np.argmax(areas)); fg=(labels==idx).astype(np.uint8)*255
                area=float((fg>0).sum()); total=float(fg.size)
                metrics['foreground_ratio']=area/max(total,1)
                ys,xs=np.where(fg>0)
                if len(xs):
                    bw=float(xs.max()-xs.min()+1); bh=float(ys.max()-ys.min()+1)
                    metrics['aspect_ratio']=bw/max(bh,1)
                edges=cv2.Canny(gray,70,150)
                metrics['edge_density']=float((edges>0).sum())/max(total,1)
                cnts,hier=cv2.findContours(fg,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    outer=[i for i,c in enumerate(cnts) if hier is None or hier[0][i][3]<0]
                    metrics['component_count']=float(max(1,len(outer)))
                    perimeter=sum(cv2.arcLength(cnts[i],True) for i in outer)
                    contour_area=sum(cv2.contourArea(cnts[i]) for i in outer)
                    metrics['contour_complexity']=float(perimeter*perimeter/max(4*math.pi*contour_area,1))
                    if hier is not None:
                        metrics['hole_count']=float(sum(1 for i in range(len(cnts)) if hier[0][i][3]>=0))
                # Approximate left/right silhouette symmetry around bbox center.
                if len(xs)>20:
                    x0,x1=int(xs.min()),int(xs.max()); crop=(fg[:,x0:x1+1]>0).astype(np.uint8)
                    if crop.shape[1]>4:
                        left=crop[:,:crop.shape[1]//2]; right=np.fliplr(crop[:,-left.shape[1]:])
                        metrics['symmetry_score']=float(1.0-np.mean(np.abs(left.astype(float)-right.astype(float))))
                evidence += 0.65
            except Exception as exc:
                reasons.append('Analisi immagine parziale: '+str(exc)[:120])
        text=(description or '').strip().lower()
        if text:
            words=re.findall(r"[\wàèéìòù'-]+",text)
            detail_terms=['dettaglio','piccolo','piccola','strisce','macchie','righe','spina','spine','corno','corna','ala','ali','orecchio','orecchie','occhio','occhi','baffi','fiocco','placca','placche','articolazione','pattern','decorazione','decorazioni','texture','squame','pelo','pelliccia','dita','zoccolo']
            part_terms=['zampa','zampe','gamba','gambe','coda','testa','muso','collo','orecchio','orecchie','ala','ali','corno','corna','braccio','braccia','gamba','gambe','corpo']
            hits=sum(text.count(t) for t in detail_terms); parts=sum(text.count(t) for t in part_terms)
            metrics['text_detail_score']=min(1.0,(hits*0.14+parts*0.08)+max(0,len(words)-18)*0.01)
            evidence += 0.35
            if hits>=2: reasons.append('La descrizione contiene molti dettagli costruttivi.')
            if parts>=3: reasons.append('La descrizione indica diverse parti separate.')
        # Score mapping is intentionally conservative.
        s=18.0
        s += min(22, metrics['component_count']*7)
        s += min(18, max(0,metrics['hole_count'])*4)
        s += min(18, max(0,metrics['edge_density']-0.025)*260)
        s += min(15, max(0,metrics['contour_complexity']-1)*3.2)
        s += min(8, metrics['text_detail_score']*8)
        if metrics['symmetry_score']>.82: s-=5
        elif metrics['symmetry_score']<.55 and evidence>.5: s+=5
        if metrics['aspect_ratio']>2.8 or (0<metrics['aspect_ratio']<.36): s+=5
        score=max(0,min(100,s))
        if score<35: level='semplice'
        elif score<60: level='medio'
        elif score<80: level='complesso'
        else: level='molto complesso'
        confidence=min(1.0,evidence)
        if metrics['component_count']>=3: reasons.append('La silhouette suggerisce più elementi/contorni distinti.')
        if metrics['edge_density']>.10: reasons.append('La superficie visibile presenta molti bordi o dettagli.')
        if metrics['hole_count']>=1: reasons.append('Sono presenti regioni interne/fori nella segmentazione.')
        if metrics['symmetry_score']>.82: reasons.append('La silhouette appare abbastanza simmetrica, utile a semplificare la costruzione.')
        if metrics['symmetry_score']<.55 and evidence>.5: reasons.append('La silhouette è asimmetrica: può richiedere parti o posizionamenti custom.')
        if score>=60: recommendations.append('Usare una scomposizione in più parti e profili custom.')
        if score>=75: recommendations.append('Prevedere una revisione manuale della struttura prima della compilazione finale.')
        if confidence<.5: recommendations.append('Fornire una foto più nitida e con soggetto ben separato dallo sfondo.')
        if image is None and text: recommendations.append('Con una foto il punteggio può essere raffinato con la silhouette reale.')
        return ComplexityReport(round(score,1),level,round(confidence,2),reasons,{k:round(v,4) for k,v in metrics.items()},recommendations)

def analyze_complexity(image=None, description=''):
    return ComplexityAnalyzer().analyze(image,description)
