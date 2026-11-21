"""
API para Fila de Atendimento (totem de atendimento presencial).

Endpoints:
    GET    /fila        -> lista os clientes não atendidos que estão na fila
    GET    /fila/{id}   -> dados do cliente na posição {id}
    POST   /fila        -> adiciona um cliente (atendimento N = normal, P = prioritário)
    PUT    /fila        -> avança a fila (todos -1; quem estava na posição 1 é atendido)
    DELETE /fila/{id}   -> remove o cliente da posição {id} e reorganiza a fila

Requisito bônus: clientes prioritários (P) entram à frente dos normais (N),
mas atrás dos prioritários que já estavam esperando.
"""

from datetime import datetime
from typing import List, Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, field_validator

FUSO = ZoneInfo("America/Sao_Paulo")

app = FastAPI(
    title="API Fila de Atendimento",
    description="API para o totem de uma fila de atendimento presencial.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Modelos (schemas)
# ---------------------------------------------------------------------------
class ClienteEntrada(BaseModel):
    """Dados enviados no POST /fila."""

    nome: str = Field(..., min_length=1, max_length=20, examples=["Maria"])
    tipo_atendimento: Literal["N", "P"] = Field(..., examples=["N"])

    @field_validator("nome", mode="before")
    @classmethod
    def limpar_nome(cls, valor):
        # Remove espaços extras para que "   " não seja aceito como nome
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("tipo_atendimento", mode="before")
    @classmethod
    def maiuscula(cls, valor):
        # Aceita "n" ou "p" e converte para maiúscula
        return valor.upper() if isinstance(valor, str) else valor


class ClienteSaida(BaseModel):
    """Dados exibidos para quem está na fila."""

    posicao: int
    nome: str
    data_chegada: datetime
    tipo_atendimento: Literal["N", "P"]


class Cliente(ClienteSaida):
    """Registro completo armazenado na 'base de dados' (memória)."""

    id: int
    atendido: bool = False


class Mensagem(BaseModel):
    mensagem: str


# ---------------------------------------------------------------------------
# "Banco de dados" em memória
# ---------------------------------------------------------------------------
clientes: List[Cliente] = []  # todos os clientes (na fila e já atendidos)
proximo_id = 1


def fila_atual() -> List[Cliente]:
    """Clientes ainda não atendidos, ordenados pela posição."""
    return sorted((c for c in clientes if not c.atendido), key=lambda c: c.posicao)


def renumerar(fila: List[Cliente]) -> None:
    """Reatribui as posições 1, 2, 3... na ordem da lista recebida."""
    for posicao, cliente in enumerate(fila, start=1):
        cliente.posicao = posicao


def buscar_por_posicao(posicao: int) -> Cliente:
    for cliente in fila_atual():
        if cliente.posicao == posicao:
            return cliente
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Nenhum cliente encontrado na posição {posicao} da fila.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def raiz():
    return {"mensagem": "API Fila de Atendimento. Documentação em /docs"}


@app.get("/fila", response_model=List[ClienteSaida], summary="Lista a fila")
def listar_fila():
    """Posição, nome e data de chegada de cada cliente não atendido.
    Se a fila estiver vazia, retorna um JSON vazio ([]) com status 200."""
    return fila_atual()


@app.get(
    "/fila/{id}",
    response_model=ClienteSaida,
    responses={404: {"model": Mensagem}},
    summary="Cliente em uma posição",
)
def obter_cliente(id: int):
    """Retorna o cliente que está na posição informada no id da fila."""
    return buscar_por_posicao(id)


@app.post(
    "/fila",
    response_model=ClienteSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona cliente na fila",
)
def adicionar_cliente(dados: ClienteEntrada):
    """Adiciona um cliente. Normais (N) vão para o fim da fila;
    prioritários (P) passam à frente dos normais, depois dos outros prioritários."""
    global proximo_id

    novo = Cliente(
        id=proximo_id,
        posicao=0,
        nome=dados.nome,
        tipo_atendimento=dados.tipo_atendimento,
        data_chegada=datetime.now(FUSO),
        atendido=False,
    )
    proximo_id += 1

    fila = fila_atual()
    if novo.tipo_atendimento == "P":
        # Insere logo após o último prioritário que está esperando
        indice = sum(1 for c in fila if c.tipo_atendimento == "P")
        fila.insert(indice, novo)
    else:
        fila.append(novo)

    clientes.append(novo)
    renumerar(fila)
    return novo


@app.put("/fila", response_model=List[ClienteSaida], summary="Avança a fila")
def avancar_fila():
    """Diminui em 1 a posição de todos da fila. Quem estava na posição 1
    vai para a posição 0 e é marcado como atendido. Retorna a fila atualizada."""
    for cliente in fila_atual():
        cliente.posicao -= 1
        if cliente.posicao == 0:
            cliente.atendido = True
    return fila_atual()


@app.delete(
    "/fila/{id}",
    response_model=Mensagem,
    responses={404: {"model": Mensagem}},
    summary="Remove cliente da fila",
)
def remover_cliente(id: int):
    """Remove o cliente da posição informada no id e atualiza a posição dos demais."""
    cliente = buscar_por_posicao(id)
    clientes.remove(cliente)
    renumerar(fila_atual())
    return {"mensagem": f"Cliente '{cliente.nome}' removido da posição {id}."}


# Padroniza o JSON de erro (ex.: 404) como {"mensagem": "..."}

@app.exception_handler(StarletteHTTPException)
async def tratar_http_exception(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"mensagem": exc.detail})
