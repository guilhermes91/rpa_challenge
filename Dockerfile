FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Aponta para o host por padrão, permitindo que o container acesse a porta 3000 da máquina local
ENV RPA_URL="https://host.docker.internal:3000"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instala dependências OS e binários headless do Chromium requeridos pelo Playwright
RUN playwright install --with-deps chromium

COPY . .

# Garante que, ao rodar no docker (interface gráfica desabilitada), sempre usará --headless se Playwright for invocado
ENTRYPOINT ["python", "rpa_solver.py"]
CMD ["--level", "all", "--mode", "native", "--headless"]
