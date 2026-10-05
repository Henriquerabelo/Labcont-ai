import io

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..importers.sigaa import ler_pdf
from ..main import render, voltar
from ..models import Importacao
from ..services import aplicar_importacao, resumo_previa

router = APIRouter(prefix="/importacao")
LIMITE_MB = 20


@router.get("")
def inicio(request: Request, db: Session = Depends(get_db)):
    historico = db.scalars(select(Importacao).order_by(Importacao.id.desc()).limit(30)).all()
    return render(request, "importacao/inicio.html", historico=historico, menu="importacao")


@router.post("")
async def enviar(request: Request, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    if not arquivo.filename.lower().endswith(".pdf") or not conteudo.startswith(b"%PDF"):
        return voltar("/importacao", erro="Envie um arquivo PDF exportado do SIGAA.")
    if len(conteudo) > LIMITE_MB * 1024 * 1024:
        return voltar("/importacao", erro=f"Arquivo acima de {LIMITE_MB} MB.")
    try:
        resultado = ler_pdf(io.BytesIO(conteudo))
    except Exception as e:  # noqa: BLE001
        return voltar("/importacao", erro=f"Não foi possível ler o PDF: {e}")
    imp = Importacao(arquivo=arquivo.filename, tipo=resultado.tipo, dados=resultado.as_dict())
    db.add(imp)
    db.commit()
    return voltar(f"/importacao/{imp.id}")


@router.get("/{id}")
def previa(request: Request, id: int, db: Session = Depends(get_db)):
    imp = db.get(Importacao, id)
    if not imp:
        return voltar("/importacao", erro="Importação não encontrada.")
    return render(request, "importacao/previa.html", imp=imp, resumo=resumo_previa(imp.dados), menu="importacao")


@router.post("/{id}/confirmar")
def confirmar(id: int, db: Session = Depends(get_db)):
    imp = db.get(Importacao, id)
    if not imp or imp.status != "PENDENTE":
        return voltar("/importacao", erro="Esta importação já foi processada.")
    imp.resumo = aplicar_importacao(db, imp.dados)
    imp.status = "CONCLUIDA"
    db.commit()
    return voltar(f"/importacao/{id}", "Importação concluída.")


@router.post("/{id}/cancelar")
def cancelar(id: int, db: Session = Depends(get_db)):
    imp = db.get(Importacao, id)
    if imp and imp.status == "PENDENTE":
        imp.status = "CANCELADA"
        db.commit()
    return voltar("/importacao", "Importação cancelada. Nada foi gravado.")
