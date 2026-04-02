# 🤖 RPA Challenge — Plataforma de Avaliação Técnica & Solver Final

Plataforma de testes para candidatos a vagas de RPA. Contém 3 desafios de autenticação de complexidade crescente.  
Este repositório possui a **aplicação alvo** e o nosso código maduro **(`rpa_solver.py`)** preparado para resolver autonomamente cada teste com total segurança e o menor tempo de processamento possível.

---

## 🎯 Objetivo (Original do Desafio)

Seu objetivo é **automatizar a autenticação** em cada um dos 3 desafios disponíveis. Cada nível exige que você analise o formulário, entenda os mecanismos de segurança e construa um bot que resolva o desafio de forma automatizada.

### 📋 Desafios Mapeados
| Nível | Descrição | Porta | Usuário Origem | Senha Origem |
|---|---|---|---|---|
| **Fácil** | Login simples com formulário | 3000 | `admin` | `rpa@2026!` |
| **Difícil** | Certificado digital mTLS + challenge dinâmico via JS (AES/CBC) | 3000 → 3001 | `operator` | `cert#Secure2026` |
| **Extremo** | Descobrir Payload Oculto via WebSockets, Resolvendo (PoW) SHA256| 3000 | `root` | `h4ck3r@Pr00f!` |

---

## 🐳 Execução via Módulo Docker em "Comando Único" (Recomendado)

Se você já possuir apenas o `docker` na máquina, copie exatamente o bloco abaixo. Ele vai:
1. Derrubar a plataforma antiga se existir.
2. Subir a API Challenge Original.
3. Extrair os certificados de criptografia.
4. "Dockernizar" de forma leve nosso código final de resolução (`rpa_solver.py`).
5. Rodar o Bot Autônomo com máxima velocidade.

```bash
docker rm -f rpa-challenge rpa-solver-bot 2>/dev/null || true && \
docker run -d -p 3000:3000 -p 3001:3001 --name rpa-challenge doc9cloud/rpa-challenge:latest && \
sleep 3 && \
docker cp rpa-challenge:/app/certs/client.pfx . && \
openssl pkcs12 -in client.pfx -clcerts -nokeys -out client_cert.pem -password pass:test123 && \
openssl pkcs12 -in client.pfx -nocerts -nodes -out client_key.pem -password pass:test123 && \
docker build -t rpa-solver-bot . && \
docker run --rm -it --add-host=host.docker.internal:host-gateway rpa-solver-bot
```
*(Nota: O Docker usará nossa configuração padrão com `--mode native`. Caso queira acionar a versão de simulação de clique Playwright, mude a última linha para `docker run --rm -it --add-host=host.docker.internal:host-gateway rpa-solver-bot --level all --mode playwright --headless`.)*

---

## 💻 Execução na Máquina Host Local (Ubuntu Limpo "Do Zero")

Se sua máquina for um Ubuntu cru (Linux limpo recém formatado sem o python) e você deseja ver os motores rodando no hospedeiro para inspeção sem sub-confinar dentro de dockers extras:
Copie e cole este mega-comando, aguarde, e a resolução acontecerá de imediato.

```bash
sudo apt-get update && \
sudo apt-get install -y python3 python3-pip python3-venv openssl docker.io && \
sudo docker rm -f rpa-challenge 2>/dev/null || true && \
sudo docker run -d -p 3000:3000 -p 3001:3001 --name rpa-challenge doc9cloud/rpa-challenge:latest && \
sleep 3 && \
sudo docker cp rpa-challenge:/app/certs/client.pfx . && \
openssl pkcs12 -in client.pfx -clcerts -nokeys -out client_cert.pem -password pass:test123 && \
openssl pkcs12 -in client.pfx -nocerts -nodes -out client_key.pem -password pass:test123 && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
playwright install --with-deps chromium && \
python rpa_solver.py --mode playwright && \
python rpa_solver.py
```

---

## 🪟 Execução na Máquina Host Local (Windows PowerShell)

Para rodar todo o ambiente local de forma automatizada e com zero resíduos no **Windows**, copie o bloco abaixo, cole inteiro no **PowerShell** e aperte `ENTER`!

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
if (!(Get-Command docker -ErrorAction SilentlyContinue)) { winget install Docker.DockerDesktop --silent --accept-package-agreements --accept-source-agreements; exit }
if (!(Get-Command python -ErrorAction SilentlyContinue)) { winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements; $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User") }
docker rm -f rpa-challenge 2>$null
docker run -d -p 3000:3000 -p 3001:3001 --name rpa-challenge doc9cloud/rpa-challenge:latest
Start-Sleep -Seconds 3
docker exec rpa-challenge sh -c "openssl pkcs12 -in /app/certs/client.pfx -clcerts -nokeys -out /app/certs/client_cert.pem -password pass:test123"
docker exec rpa-challenge sh -c "openssl pkcs12 -in /app/certs/client.pfx -nocerts -nodes -out /app/certs/client_key.pem -password pass:test123"
docker cp rpa-challenge:/app/certs/client_cert.pem .
docker cp rpa-challenge:/app/certs/client_key.pem .
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python rpa_solver.py --mode playwright
python rpa_solver.py
```

---

## 📊 Arquitetura do RPA Solver & Benchmarks

A estrutura projetada em `rpa_solver.py` expõe um padrão isolado *Factory* de processamento livre de *warnings*:
- **Native (`requests` / `websockets`)**: Bypass da interface visual (DOM), quebra dos headers e intercepção veloz e encriptação *CPU bound*.
- **Playwright (`async_playwright`)**: Instância Chromium automatizada orientada a objetos com escopo local simulando o percurso exato exigido na plataforma sem sujar `cookies` para o próximo container. Mestre para depuração ou detecções pesadas.

### ⏱️ Comparativo Real de Execução (Logs Capturados do Terminal)

**Execução Módulo Nativo (Motor de alta Performance & Bypass de UI):** *Tempo Total ~0.85s*
```text
[EASY] Início (Tentativa 1/3): 14:21:37.800
[EASY] Fim:    14:21:37.821
[EASY] Duração: 21.03 ms
    message: Autenticação bem-sucedida!
    token: 77e152bc31bdaae9e45b58210dc229ef7a2293e98f1154ff7d9fc8b1491e7957
    elapsed_ms: 0
    level: easy

[HARD] Início (Tentativa 1/3): 14:21:37.822
[HARD] Fim:    14:21:37.858
[HARD] Duração: 36.36 ms
    token: 9e22e241379c0d41584f9186222c9180c8cd33a202f6848d50534392e3f72c9a
    message: ✅ Autenticação Completa!

[EXTREME] Início (Tentativa 1/3): 14:21:37.859
[EXTREME] Fim:    14:21:38.649
[EXTREME] Duração: 790.32 ms
    message: 🎉 Parabéns! Autenticação completa com sucesso!
    token: 4aeb863b09b4d8de5cae0f16b318d3396f7e45f30906f3c27d2712aed7e742b6596ea5601994c61cf271cd4ca473fb2a
    elapsed_ms: 773
    level: extreme
    proof_hash: 0c4431a6d6b427d77b4233f38d841f485190d4be6fd85c1dae3f3307d5f196de

[ALL] Tempo Total Combinado: 851.00 ms
```

**Execução Módulo Playwright (Simulação Browser Visual):**
```text
[*] ENGINE INICIADA
    ALVO: ALL
    MODO: PLAYWRIGHT
    UI:   ABERTO
    MAX RETRY: 3

[EASY] Início (Tentativa 1/3): 14:21:49.964
[EASY] Fim:    14:21:53.301
[EASY] Duração: 3337.37 ms
    message: Login Simples

[HARD] Início (Tentativa 1/3): 14:21:53.302
[HARD] Fim:    14:21:57.837
[HARD] Duração: 4535.22 ms
    message: Certificado Digital + Hash

[EXTREME] Início (Tentativa 1/3): 14:21:57.838
[EXTREME] Fim:    14:22:37.114
[EXTREME] Duração: 39276.32 ms
    message: ✅ Autenticado! (35729ms)
    
[ALL] Tempo Total Combinado: 47150.91 ms
```

---

## ❓ FAQ & Argumentos da CLI (Command Line Interface)

O motor `rpa_solver.py` foi fortemente aprimorado com recursos de **Logging Global** blindados e **Loops de Recuperação (Auto-Retry)**. Modifique suas baterias de execução manipulando os argumentos:

| Argumento | Opções Aceitas | Valor Padrão (Omissão) | Descrição e Comportamento |
| :--- | :--- | :--- | :--- |
| `--level` | `easy`\|`hard`\|`extreme`\|`all` | `all` | Define o nível do desafio a se resolver. |
| `--mode` | `native`\|`playwright` | `native` | O **Native** opera TCP Sockets cegos e bypass. **Playwright** sobe a renderização injetada em engine Chromium. |
| `--headless` | *Flag Solitária Opcional* | *(Falso)* | Se passada, Ocultará o Chromium em instâncias virtuais ou containers (`xvfb` Like) |
| `--retries` | *integernum (Ex: 5)* | `3` | Define o "Teto de Retentativas" sob as quais os motores vão insistir a resolução em caso de timeout de DOM ou perda de Socket. |

*Exemplo Extra Avançado – Rodando o módulo Extreme no Front simulado pela tela de fundo invisível realizando 10 baterias de insistência nativa em eventuais engasgos do localhost:*
```bash
python rpa_solver.py --level extreme --mode playwright --headless --retries 10
```
