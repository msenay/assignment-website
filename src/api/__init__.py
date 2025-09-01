
from __future__ import annotations
import os
from typing import Optional, Dict, Any, Callable
import httpx

# Langfuse v3 (OTel tabanlı)
from langfuse import Langfuse, observe


class LFManager:
    """Langfuse v3 için minimalist yardımcı.

    - PEM (özel CA) => httpx.verify + OTEL exporter sertifikası
    - Opsiyonel: ekstra header (örn. CAAS token) tüm Langfuse HTTP çağrılarına
    - @observe ve context manager kısayolları
    - LLM entegrasyonu:
        * OpenAI drop-in (langfuse.openai) => otomatik generation tracing
        * Generic HTTPX LLM çağrısı => kendi LLM endpoint'in
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
        # httpx client: Langfuse SDK v3'ün non-tracing HTTP istekleri için
        httpx_kwargs: Dict[str, Any] = {"timeout": timeout}
        if ca_pem_path:
            httpx_kwargs["verify"] = ca_pem_path
            # OTel exporter'ın da aynı CA'ya güvenmesi için:
            os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE", ca_pem_path)

        self.httpx_client = httpx.Client(**httpx_kwargs)

        # Ek header gerekiyorsa (ör. proxy/caas gateway token)
        # Not: Langfuse auth yine PK/SK ile, bu header ek olarak geçer.
        if extra_headers:
            self.httpx_client.headers.update(extra_headers)

        # Parametreleri Langfuse client'a aktar
        cfg: Dict[str, Any] = {
            "environment": environment,
            "timeout": timeout,
            "debug": debug,
            "tracing_enabled": tracing_enabled,
            "httpx_client": self.httpx_client,
        }
        if host:
            cfg["host"] = host
        if public_key:
            cfg["public_key"] = public_key
        if secret_key:
            cfg["secret_key"] = secret_key

        self.lf = Langfuse(**cfg)

    # ---------- Ergonomik kısayollar ----------
    @staticmethod
    def observe(*dargs, **dkwargs):
        return observe(*dargs, **dkwargs)

    def start_span(self, name: str, **kw):
        return self.lf.start_as_current_span(name=name, **kw)

    def start_generation(self, name: str, model: Optional[str] = None, **kw):
        return self.lf.start_as_current_generation(name=name, model=model, **kw)

    def update_current_span(self, **kw):
        return self.lf.update_current_span(**kw)

    def update_current_generation(self, **kw):
        return self.lf.update_current_generation(**kw)

    def update_current_trace(self, **kw):
        return self.lf.update_current_trace(**kw)

    def get_prompt(self, name: str):
        return self.lf.get_prompt(name=name)

    def get_current_trace_id(self):
        return self.lf.get_current_trace_id()

    def get_current_observation_id(self):
        return self.lf.get_current_observation_id()

    def flush(self):
        self.lf.flush()

    def shutdown(self):
        # Langfuse'ı ve httpx client'ı kapat
        self.lf.shutdown()
        try:
            self.httpx_client.close()
        except Exception:
            pass

    # Context manager desteği
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.shutdown()

    # ---------- LLM: OpenAI drop-in (langfuse.openai) ----------
    def openai_chat(
        self,
        *,
        model: str,
        messages: list,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """OpenAI Chat Completion; Langfuse entegrasyonu otomatik trace/generation üretir.
        Not: Aktif bir span içinde çağırırsan hiyerarşi doğru oluşur (nesting).
        """
        # Import'u burada yapıyoruz; paket yoksa manager yine çalışsın
        from langfuse.openai import openai

        client = openai.OpenAI()
        # İsteğe bağlı olarak üstte bir span açmak istersen:
        span_name = name or "openai.chat"
        with self.start_span(span_name):
            # name + metadata Langfuse tarafından generation'a işlenir
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                name=name,             # Langfuse jenerasyon adı
                metadata=metadata,     # Langfuse jenerasyon metadata/trace attrs
                **kwargs,              # stream, temperature, tools vs.
            )
        return response

    # ---------- LLM: Generic HTTPX çağrısı ----------
    def llm_httpx(
        self,
        *,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        name: str = "llm.httpx",
        model: Optional[str] = None,
        extract_output: Optional[Callable[[Any], Any]] = None,
        # extract_output: response.json() -> output (varsayılan: OpenAI benzeri şema)
    ) -> Any:
        """Kendi LLM endpoint'in için generic çağrı + Langfuse generation.

        - PEM/extra_headers zaten httpx client'a uygulandı.
        - extract_output yoksa OpenAI benzeri JSON'dan text ayıklamayı dener.
        """
        with self.start_generation(name=name, model=model) as gen:
            gen.update(input=payload)

            resp = self.httpx_client.request(method.upper(), url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text

            if extract_output:
                output = extract_output(data)
            else:
                # OpenAI benzeri JSON şemasından en yaygın yolu dene
                output = None
                if isinstance(data, dict):
                    try:
                        output = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content")
                        )
                    except Exception:
                        output = None
                if output is None:
                    output = data  # son çare tüm data

            # Kullanıcı isterse usage/cost'u kendisi ekleyebilir; burada sadece output'u işleriz
            gen.update(output=output)
            return data



# demo.py
# demo.py
import os
from lf_manager import LFManager

"""
Çalışma mantığı:
- Varsa OPENAI_API_KEY => OpenAI drop-in ile otomatik tracing (Langfuse generation).
- Yoksa generic HTTPX çağrısı (postman-echo.com/post) ile demo.
- PEM (CA) ve CAAS token desteklenir.
"""

def main():
    manager_kwargs = {
        "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
        "environment": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
        "ca_pem_path": os.getenv("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"),  # /path/to/ca.pem
        "debug": False,
        "tracing_enabled": True,
    }

    extra_headers = {}
    caas_token = os.getenv("CAAS_API_TOKEN")
    if caas_token:
        extra_headers["Authorization"] = caas_token
    if extra_headers:
        manager_kwargs["extra_headers"] = extra_headers

    with LFManager(**manager_kwargs) as manager:
        # Kök span: trace metadata'yı erken set edelim
        with manager.start_span(name="demo-request") as root:
            root.update_trace(user_id="demo-user", tags=["demo", "pem", "v3"])

            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                # --- Yol A: OpenAI drop-in (langfuse.openai) ---
                print("Running OpenAI drop-in demo…")
                try:
                    resp = manager.openai_chat(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[{"role": "user", "content": "Say hello in one sentence."}],
                        name="demo-openai-generation",
                        metadata={
                            # Trace attribute kısayollarını metadata ile verebilirsin
                            "langfuse_session_id": "session_demo",
                            "langfuse_user_id": "demo-user",
                            "langfuse_tags": ["openai", "demo"],
                        },
                    )
                    content = resp.choices[0].message.content
                    print("OpenAI content:", content)
                    # Sonuca ufak bir puan
                    root.score_trace(name="openai_has_content", value=1.0 if content else 0.0)
                except Exception as e:
                    print("OpenAI demo skipped due to error:", e)
                    openai_api_key = None  # fallback yap

            if not openai_api_key:
                # --- Yol B: Generic HTTPX (LLM endpoint'in yoksa echo ile gösterim) ---
                print("Running HTTPX echo demo…")
                url = os.getenv("LLM_URL", "https://postman-echo.com/post")

                data = manager.llm_httpx(
                    url=url,
                    payload={
                        "model": "demo-model",
                        "messages": [{"role": "user", "content": "Ping?"}],
                    },
                    name="demo-httpx-generation",
                    model="demo-model",
                    # CAAS token'ı per-call header yerine global header olarak da verdik (extra_headers),
                    # yine de istersen burada override edebilirsin:
                    headers=None,
                    # echo servisten output'u nasıl çıkaralım?
                    extract_output=lambda d: d.get("json") if isinstance(d, dict) else d,
                )
                print("HTTPX response (truncated repr):", repr(data)[:200])
                root.score_trace(name="httpx_call_ok", value=1.0)

        # Kısa ömürlü script => flush önemli
        manager.flush()

if __name__ == "__main__":
    main()



