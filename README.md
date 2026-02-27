# 🤖 RPA Challenge — Plataforma de Avaliação Técnica

Plataforma de testes para candidatos a vagas de RPA.  
3 desafios de autenticação com complexidade crescente.

---

## 🎯 Objetivo

Seu objetivo é **automatizar a autenticação** em cada um dos 3 desafios disponíveis. Cada nível exige que você analise o formulário, entenda os mecanismos de segurança e construa um bot que resolva o desafio de forma automatizada.

### O que será avaliado

- **Domínio sobre o problema** — capacidade de analisar, compreender e contornar mecanismos de autenticação
- **Otimização de recursos** — eficiência no uso de memória, rede e processamento
- **Tempo de execução** — quanto mais rápido seu bot completar os desafios, melhor
- **Qualidade do código** — organização, clareza e boas práticas

### Linguagens aceitas

- **Python** (preferencial)
- Go
- JavaScript / TypeScript

> Pode ser usada qualquer linguagem, mas dê preferência às listadas acima.

---

## 🚀 Como executar

```bash
docker pull doc9cloud/rpa-challenge:latest
docker run -d -p 3000:3000 -p 3001:3001 --name rpa-challenge doc9cloud/rpa-challenge:latest
```

Acesse: **https://localhost:3000**

> ⚠️ O certificado é auto-assinado. Configure seu bot para aceitar certificados self-signed.

---

## 📋 Desafios

| Nível | Descrição | Porta |
|---|---|---|
| **Fácil** | Login simples com formulário | 3000 |
| **Difícil** | Certificado digital mTLS + challenge dinâmico via JavaScript | 3000 → 3001 |
| **Extremo** | Descubra e automatize o fluxo | 3000 |

### Como funciona

1. **Acesse a página** de cada desafio e analise o código-fonte (HTML, JS, requisições de rede)
2. **Identifique** os endpoints, parâmetros e mecanismos de segurança
3. **Construa seu bot** que automatize todo o fluxo de autenticação
4. **O bot deve retornar** o token de autenticação e o tempo de execução

---

## 🔑 Credenciais

| Nível | Usuário | Senha |
|---|---|---|
| Fácil | `admin` | `rpa@2026!` |
| Difícil | `operator` | `cert#Secure2026` |
| Extremo | `root` | `h4ck3r@Pr00f!` |

---

## 📜 Certificado Digital

O desafio difícil exige um certificado digital do cliente (mTLS). Extraia os arquivos do container:

```bash
docker cp rpa-challenge:/app/certs/client.pfx .
docker cp rpa-challenge:/app/certs/ca.crt .
```

Senha do PFX: `test123`

---

## 📦 Entrega

Envie seu código em um repositório Git (público ou privado) contendo:

- Código-fonte do bot
- `README.md` com instruções de execução
- Tempo de execução de cada desafio registrado na saída do programa
