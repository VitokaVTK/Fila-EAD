API Fila de Atendimento (FastAPI)

Como executar
1. python -m venv .venv
2. .venv\Scripts\activate   (no Linux/Mac: source .venv/bin/activate)
3. pip install -r requirements.txt
4. uvicorn main:app --reload
5. Abrir no navegador: http://127.0.0.1:8000/docs

Endpoints
GET    /fila       Lista os clientes não atendidos (posição, nome e data de chegada)
GET    /fila/{id}  Cliente na posição informada (404 se não existir)
POST   /fila       Adiciona cliente. Ex.: {"nome": "Maria", "tipo_atendimento": "N"}
PUT    /fila       Avança a fila; quem estava na posição 1 é marcado como atendido
DELETE /fila/{id}  Remove o cliente da posição informada (404 se não existir)

Bônus: clientes prioritários (P) entram à frente dos normais (N).
Heroku: os arquivos Procfile e .python-version já estão prontos para o deploy.
