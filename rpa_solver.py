import os
os.environ["NODE_OPTIONS"] = "--no-deprecation"
import sys
import ssl
import time
import json
import asyncio
import hashlib
import argparse
import logging
import urllib3
import requests
import websockets
import string
import random
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Type
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from playwright.async_api import async_playwright, BrowserContext

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class Level(str, Enum):
    EASY = "easy"
    HARD = "hard"
    EXTREME = "extreme"
    ALL = "all"

class Mode(str, Enum):
    NATIVE = "native"
    PLAYWRIGHT = "playwright"

def _resolve_base_url() -> str:
    url = os.getenv("RPA_URL", "https://localhost:3000")
    if "host.docker.internal" in url:
        if not os.path.exists("/.dockerenv"):
            url = url.replace("host.docker.internal", "localhost")
        else:
            import socket
            try:
                socket.gethostbyname("host.docker.internal")
            except socket.gaierror:
                fallback_ip = "172.17.0.1"
                try:
                    with open("/proc/net/route") as f:
                        for line in f.readlines()[1:]:
                            fields = line.strip().split()
                            if fields[1] == '00000000':
                                gw = fields[2]
                                fallback_ip = ".".join(str(int(gw[i:i+2], 16)) for i in range(6, -1, -2))
                                break
                except Exception:
                    pass
                url = url.replace("host.docker.internal", fallback_ip)
    return url

@dataclass(frozen=True)
class ChallengeConfig:
    base_url: str = _resolve_base_url()
    base_dir: Path = Path(__file__).parent.resolve()

class SecurityUtils:
    @staticmethod
    def solve_pow(prefix: str, difficulty: int) -> str:
        target = "0" * difficulty
        nonce_value = 0
        while True:
            nonce = str(nonce_value)
            h = hashlib.sha256((prefix + nonce).encode()).hexdigest()
            if h.startswith(target):
                return nonce
            nonce_value += 1

    @staticmethod
    def decrypt_aes_cbc(encrypted_payload: str, session_id: str, secret_key: str) -> str:
        iv_hex, cipher_hex = encrypted_payload.split(':')
        iv = bytes.fromhex(iv_hex)
        ciphertext = bytes.fromhex(cipher_hex)
        key_str = session_id + secret_key
        key = hashlib.sha256(key_str.encode()).digest()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = cipher.decrypt(ciphertext)
        plaintext = unpad(padded, AES.block_size)
        return json.loads(plaintext).get("otp", "")

class RpaSolver:
    def __init__(self, config: ChallengeConfig, headless: bool = True) -> None:
        self.config = config
        self.headless = headless
        
    async def solve(self) -> Dict[str, Any]:
        raise NotImplementedError

class NativeEasySolver(RpaSolver):
    async def solve(self) -> Dict[str, Any]:
        url = f"{self.config.base_url}/api/easy/login"
        payload = {"username": "admin", "password": "rpa@2026!"}
        
        with requests.Session() as session:
            session.verify = False
            response = session.post(url, json=payload)
            response.raise_for_status()
            return response.json()

class NativeHardSolver(RpaSolver):
    async def solve(self) -> Dict[str, Any]:
        login_url = f"{self.config.base_url}/api/hard/login"
        secret = "rpa_hard_challenge_2026"
        cert_path = str(self.config.base_dir / "client_cert.pem")
        key_path = str(self.config.base_dir / "client_key.pem")
        
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            return {"success": False, "message": "Certificados mTLS não encontrados. Extraia e converta via openssl e forneça no dirtório base."}
            
        timestamp = str(int(time.time() * 1000))
        nonce = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        challenge = hashlib.sha256((timestamp + nonce + secret).encode()).hexdigest()
        
        payload = {
            "username": "operator",
            "password": "cert#Secure2026",
            "challenge": challenge,
            "timestamp": timestamp,
            "nonce": nonce
        }
        
        with requests.Session() as session:
            session.verify = False
            resp1 = session.post(login_url, json=payload)
            resp1.raise_for_status()
            data1 = resp1.json()
            
            if not data1.get("success"):
                return data1
                
            redirect_url = data1.get("redirect", "")
            if redirect_url.startswith("/"):
                redirect_url = f"{self.config.base_url}{redirect_url}"
            else:
                base_host = urlparse(self.config.base_url).hostname
                r_parsed = urlparse(redirect_url)
                if r_parsed.hostname in ("localhost", "127.0.0.1") and base_host:
                    redirect_url = redirect_url.replace(f"://{r_parsed.hostname}", f"://{base_host}", 1)
                
            parsed = urlparse(redirect_url)
            token = parse_qs(parsed.query).get("token", [""])[0]
            
            with requests.Session() as mtls_session:
                mtls_session.cert = (cert_path, key_path)
                mtls_session.verify = False
                resp2 = mtls_session.get(redirect_url)
                resp2.raise_for_status()
                
                content_type = resp2.headers.get("content-type", "")
                if "application/json" in content_type:
                    data2 = resp2.json()
                    success = data2.get("success", False)
                    message = data2.get("message", "")
                else:
                    success = resp2.status_code == 200
                    html_body = resp2.text
                    match = re.search(r'class="success[^"]*"[^>]*>([^<]+)', html_body)
                    if not match:
                        match = re.search(r'<h[12][^>]*>([^<]+)', html_body)
                    message = match.group(1).strip() if match else ("OK" if success else "Falha")
                    
        return {"success": success, "token": token, "message": message}

class NativeExtremeSolver(RpaSolver):
    async def solve(self) -> Dict[str, Any]:
        init_url = f"{self.config.base_url}/api/extreme/init"
        verify_url = f"{self.config.base_url}/api/extreme/verify-token"
        complete_url = f"{self.config.base_url}/api/extreme/complete"
        
        parsed_url = urlparse(self.config.base_url)
        ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'
        ws_url = f"{ws_scheme}://{parsed_url.netloc}/ws"
        
        with requests.Session() as session:
            session.verify = False
            resp_init = session.post(init_url)
            resp_init.raise_for_status()
            data_init = resp_init.json()
            
            ticket = data_init.get('ws_ticket')
            session_id = data_init.get('session_id')
            
            if not ticket or not session_id:
                return {"success": False, "message": "Falha na inicializacao"}
                
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ws_uri = f"{ws_url}?ticket={ticket}&session_id={session_id}"
            
            async with websockets.connect(ws_uri, ssl=ssl_context) as ws:
                msg1 = await ws.recv()
                pow_req = json.loads(msg1)
                
                if pow_req.get("type") == "pow_challenge":
                    nonce = SecurityUtils.solve_pow(pow_req.get("prefix", ""), pow_req.get("difficulty", 5))
                    await ws.send(json.dumps({"nonce": nonce}))
                    msg2 = await ws.recv()
                    pow_res = json.loads(msg2)
                    
                    if not pow_res.get("success"):
                        return pow_res
                    
                    intermediate_token = pow_res.get("intermediate_token", "")
            
            resp_ver = session.post(verify_url, json={"session_id": session_id, "intermediate_token": intermediate_token})
            resp_ver.raise_for_status()
            data_ver = resp_ver.json()
            
            if not data_ver.get("success"):
                return data_ver
                
            otp = SecurityUtils.decrypt_aes_cbc(data_ver.get("encrypted_payload", ""), session_id, "extreme_secret_key")
            
            resp_comp = session.post(complete_url, json={
                "session_id": session_id,
                "otp": otp,
                "username": "root",
                "password": "h4ck3r@Pr00f!"
            })
            resp_comp.raise_for_status()
            return resp_comp.json()

class PlaywrightGenericSolver(RpaSolver):
    def __init__(self, config: ChallengeConfig, headless: bool, url_path: str, final_locator: str) -> None:
        super().__init__(config, headless)
        self.url_path = url_path
        self.final_locator = final_locator

    async def _configure_context(self, browser) -> BrowserContext:
        kwargs: Dict[str, Any] = {"ignore_https_errors": True}
        cert_path = str(self.config.base_dir / "client_cert.pem")
        key_path = str(self.config.base_dir / "client_key.pem")
        
        if "hard" in self.url_path and os.path.exists(cert_path) and os.path.exists(key_path):
            kwargs["client_certificates"] = [{
                "origin": "*",
                "certPath": cert_path,
                "keyPath": key_path
            }]
            
        try:
            return await browser.new_context(**kwargs)
        except Exception:
            return await browser.new_context(ignore_https_errors=True)

    async def solve(self) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await self._configure_context(browser)
            page = await context.new_page()
            target_url = f"{self.config.base_url}{self.url_path}"
            
            await page.goto(target_url)
            
            try:
                if "extreme" in self.url_path:
                    await page.click("#demoBtn")
                    await page.wait_for_function(
                        "() => { const el = document.getElementById('step5-status'); return el && (el.innerText.includes('✅') || el.innerText.includes('Falha')); }",
                        timeout=180000
                    )
                    status_text = await page.locator(self.final_locator).inner_text()
                else:
                    await page.fill('input[name="username"]', "admin" if "easy" in self.url_path else "operator")
                    await page.fill('input[name="password"]', "rpa@2026!" if "easy" in self.url_path else "cert#Secure2026")
                    await page.click('button[type="submit"]')
                    await page.wait_for_selector(self.final_locator, timeout=30000)
                    status_text = await page.locator(self.final_locator).first.inner_text()
                    
                return {"success": True, "message": status_text}
                
            except Exception as e:
                return {"success": False, "message": str(e)}
            finally:
                if not self.headless:
                    await asyncio.sleep(2)
                await browser.close()

class PlaywrightEasySolver(PlaywrightGenericSolver):
    def __init__(self, config: ChallengeConfig, headless: bool) -> None:
        super().__init__(config, headless, "/easy/", ".success, .alert, h1, h2")

class PlaywrightHardSolver(PlaywrightGenericSolver):
    def __init__(self, config: ChallengeConfig, headless: bool) -> None:
        super().__init__(config, headless, "/hard/", ".success, .alert, h1, h2")

class PlaywrightExtremeSolver(PlaywrightGenericSolver):
    def __init__(self, config: ChallengeConfig, headless: bool) -> None:
        super().__init__(config, headless, "/extreme/", "#step5-status")

class SolverFactory:
    @staticmethod
    def create(level: Level, mode: Mode, config: ChallengeConfig, headless: bool) -> RpaSolver:
        registry: Dict[Mode, Dict[Level, Type[RpaSolver]]] = {
            Mode.NATIVE: {
                Level.EASY: NativeEasySolver,
                Level.HARD: NativeHardSolver,
                Level.EXTREME: NativeExtremeSolver
            },
            Mode.PLAYWRIGHT: {
                Level.EASY: PlaywrightEasySolver,
                Level.HARD: PlaywrightHardSolver,
                Level.EXTREME: PlaywrightExtremeSolver
            }
        }
        return registry[mode][level](config, headless)

class ExecutionEngine:
    def __init__(self, mode: Mode, headless: bool, retries: int) -> None:
        self.mode = mode
        self.headless = headless
        self.retries = retries
        self.config = ChallengeConfig()
        
    async def run_single(self, level: Level) -> None:
        solver = SolverFactory.create(level, self.mode, self.config, self.headless)
        
        for attempt in range(1, self.retries + 1):
            start_time = datetime.now()
            start_perf = time.perf_counter()
            
            logger.info(f"\033[93m[{level.value.upper()}] Início (Tentativa {attempt}/{self.retries}): {start_time.strftime('%H:%M:%S.%f')[:-3]}\033[0m")
            
            try:
                result = await solver.solve()
                end_perf = time.perf_counter()
                end_time = datetime.now()
                duration = (end_perf - start_perf) * 1000
                
                success = result.get('success', False)
                c_code = "\033[92m" if success else "\033[91m"
                logger.info(f"{c_code}[{level.value.upper()}] Fim:    {end_time.strftime('%H:%M:%S.%f')[:-3]}\033[0m")
                logger.info(f"{c_code}[{level.value.upper()}] Duração: {duration:.2f} ms\033[0m")
                
                for k, v in result.items():
                    if k not in ['success']:
                        logger.info(f"    {k}: {v}")
                
                if success:
                    break
                elif attempt < self.retries:
                    logger.info(f"\033[93m[{level.value.upper()}] Retentando...\033[0m\n")
                    await asyncio.sleep(1)
                        
            except Exception as e:
                logger.error(f"\033[91m[{level.value.upper()}] ERRO FATAL na tentativa {attempt}: {str(e)}\033[0m")
                if attempt < self.retries:
                    logger.info(f"\033[93m[{level.value.upper()}] Retentando...\033[0m\n")
                    await asyncio.sleep(1)
            
        logger.info("")

    async def run_all(self) -> None:
        levels = [Level.EASY, Level.HARD, Level.EXTREME]
        global_start = time.perf_counter()
        
        for level in levels:
            await self.run_single(level)
            
        global_duration = (time.perf_counter() - global_start) * 1000
        logger.info(f"\033[96m[ALL] Tempo Total Combinado: {global_duration:.2f} ms\033[0m")

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=str, choices=[l.value for l in Level], default="all", help="Alvo de Resolução")
    parser.add_argument("--mode", type=str, choices=[m.value for m in Mode], default="native", help="Engine de Operação")
    parser.add_argument("--headless", action="store_true", default=False, help="Executar de forma cega")
    parser.add_argument("--retries", type=int, default=3, help="Tentativas máximas de sucesso do solver antes de abortar")
    args = parser.parse_args()
    
    level = Level(args.level)
    mode = Mode(args.mode)
    
    logger.info(f"\033[96m[*] ENGINE INICIADA")
    logger.info(f"    ALVO: {level.value.upper()}")
    logger.info(f"    MODO: {mode.value.upper()}")
    logger.info(f"    UI:   {'FECHADO' if args.headless else 'ABERTO'}")
    logger.info(f"    MAX RETRY: {args.retries}\033[0m\n")
    
    engine = ExecutionEngine(mode, args.headless, args.retries)
    
    if level == Level.ALL:
        await engine.run_all()
    else:
        await engine.run_single(level)

if __name__ == "__main__":
    if sys.platform == 'win32':
        is_native = ("native" in sys.argv) or ("--mode" not in sys.argv)
        if is_native:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', DeprecationWarning)
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
