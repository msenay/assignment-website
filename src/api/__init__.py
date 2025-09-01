# lf_manager.py
from __future__ import annotations
import os
import httpx
from typing import Optional, Dict, Any
from langfuse import Langfuse, get_client, observe

class LFManager:
    """Langfuse v3 için minimalist yardımcı.

    - PEM (özel CA) => httpx.verify + OTEL exporter sertifikası
    - Opsiyonel: ekstra header (örn. CAAS token) tüm Langfuse HTTP çağrılarına
    - @observe ve context manager kısayolları
    """
    def __init__(
        self,
        *,
        host: Optional[str] = None,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        environment: str = "development",
        timeout: float = 10.0,
        ca_pem_path: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,  # örn {"Authorization": "Bearer ..."}
        debug: bool = False,
        tracing_enabled: bool = True,
    ):
        # httpx client: Langfuse SDK v3'ün non-tracing istekleri için
        httpx_kwargs: Dict[str, Any] = {"timeout": timeout}
        if ca_pem_path:
            httpx_kwargs["verify"] = ca_pem_path
            # OTel exporter'ın da aynı CA'ya güvenmesi için:
            os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE", ca_pem_path)

        client = httpx.Client(**httpx_kwargs)

        # Ek header gerekiyorsa (ör. proxy/caas gateway token)
        # Not: Langfuse auth yine PK/SK ile, bu header ek olarak geçer.
        if extra_headers:
            # httpx’te default header set etmek:
            client.headers.update(extra_headers)

        # Env yoksa doğrudan parametrelerden al
        cfg: Dict[str, Any] = {}
        if host: cfg["host"] = host
        if public_key: cfg["public_key"] = public_key
        if secret_key: cfg["secret_key"] = secret_key
        cfg.update({
            "environment": environment,
            "timeout": timeout,
            "debug": debug,
            "tracing_enabled": tracing_enabled,
            "httpx_client": client,
        })

        self.lf = Langfuse(**cfg)

    # Kısayollar
    @staticmethod
    def observe(*dargs, **dkwargs):
        return observe(*dargs, **dkwargs)

    def start_span(self, name: str, **kw):
        return self.lf.start_as_current_span(name=name, **kw)

    def start_generation(self, name: str, model: Optional[str] = None, **kw):
        return self.lf.start_as_current_generation(name=name, model=model, **kw)

    def update_current_span(self, **kw): return self.lf.update_current_span(**kw)
    def update_current_generation(self, **kw): return self.lf.update_current_generation(**kw)
    def update_current_trace(self, **kw): return self.lf.update_current_trace(**kw)

    def get_prompt(self, name: str): return self.lf.get_prompt(name=name)
    def get_current_trace_id(self): return self.lf.get_current_trace_id()
    def get_current_observation_id(self): return self.lf.get_current_observation_id()

    def flush(self): self.lf.flush()
    def shutdown(self): self.lf.shutdown()

# demo.py
import os
from lf_manager import LFManager, observe

manager = LFManager(
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
    ca_pem_path=os.getenv("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"),
    extra_headers=({"Authorization": os.getenv("CAAS_API_TOKEN")} 
                   if os.getenv("CAAS_API_TOKEN") else None),
)

@observe(name="prepare", capture_input=False, capture_output=True)
def prepare(n: int) -> dict:
    return {"nums": list(range(n))}

def main():
    with manager.start_span(name="request") as root:
        # Trace metadata (LLM-judge/evaluation için önemli)
        root.update_trace(user_id="u-123", tags=["demo", "pem"])

        payload = prepare(3)

        with manager.start_generation(name="llm-call", model="gpt-4o-mini") as gen:
            gen.update(input={"messages": [{"role":"user", "content":"Ping?"}], "payload": payload})
            # ... burada gerçek LLM çağrın olur ...
            gen.update(output="Pong!", usage_details={"input_tokens": 5, "output_tokens": 7})

        root.update_trace(input={"question": "Ping?"}, output={"answer": "Pong!"})

    # kısa ömürlü script’te flush/shutdown
    manager.flush()
    manager.shutdown()

if __name__ == "__main__":
    main()


# lf_manager.py (ek öneriler)

class LFManager:
    ...
    def shutdown(self):
        # 1) Langfuse tarafını kapat
        self.lf.shutdown()
        # 2) httpx client'ı da kapat (varsa)
        try:
            client = getattr(self.lf, "config", None) and getattr(self.lf.config, "httpx_client", None)
            if client:
                client.close()
        except Exception:
            pass

    # İstersen context manager:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self.shutdown()

