"""Central de documentos da dupla (Etapa 4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..documentos import gerar_documentos
from ..main import render, voltar
from ..models_dupla import Dupla

router = APIRouter()
TIPOS = {"nfe": "NF-e", "cte": "CT-e", "nfse": "NFS-e", "fatura": "Fatura", "rpa": "RPA", "contrato": "Contrato", "auto": "Auto de infração"}


def _dupla(db, id):
    d = db.get(Dupla, id)
    return d if d and d.empresa else None


@router.get("/duplas/{id}/documentos")
def lista(request: Request, id: int, db: Session = Depends(get_db)):
    d = _dupla(db, id)
    if not d:
        return voltar("/duplas", erro="Gere a empresa da dupla antes dos documentos.")
    docs = gerar_documentos(d.empresa.valores)
    return render(request, "documentos/lista.html", d=d, docs=docs, tipos=TIPOS, menu="duplas")


@router.get("/duplas/{id}/documentos/{doc_id}")
def ver(request: Request, id: int, doc_id: str, db: Session = Depends(get_db)):
    d = _dupla(db, id)
    if not d:
        return voltar("/duplas", erro="Gere a empresa da dupla antes dos documentos.")
    docs = gerar_documentos(d.empresa.valores)
    i = next((k for k, x in enumerate(docs) if x["id"] == doc_id), None)
    if i is None:
        return voltar(f"/duplas/{id}/documentos", erro="Documento não encontrado.")
    return render(request, "documentos/doc.html", d=d, doc=docs[i], tipos=TIPOS, menu="duplas",
                  anterior=docs[i - 1]["id"] if i > 0 else None, proximo=docs[i + 1]["id"] if i + 1 < len(docs) else None)
