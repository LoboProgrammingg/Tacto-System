"""Streamlit onboarding UI for Tacto-System.

Run locally:
    cd admin
    pip install -r requirements.txt
    cp .env.example .env  # fill in values
    streamlit run app.py
"""

from __future__ import annotations

import base64
import json
import os
import time
import unicodedata
from pathlib import Path
from typing import Any

import streamlit as st

try:
    # Real-time search-as-you-type. Falls back to st.text_input (Enter to apply).
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None

from api_client import JoinClient, TactoFlowClient
from config import Settings, get_settings


ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "tacto_logo.png"
REMEMBERED_PATH = Path(__file__).parent / ".remembered_login.json"


def _load_remembered() -> dict[str, str]:
    if not REMEMBERED_PATH.exists():
        return {}
    try:
        return json.loads(REMEMBERED_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_remembered(email: str, password: str) -> None:
    try:
        REMEMBERED_PATH.write_text(json.dumps({"email": email, "password": password}))
        os.chmod(REMEMBERED_PATH, 0o600)
    except OSError:
        pass


def _clear_remembered() -> None:
    try:
        REMEMBERED_PATH.unlink(missing_ok=True)
    except OSError:
        pass


@st.cache_data(show_spinner=False)
def _logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@st.cache_data(ttl=30, show_spinner=False)
def _cached_health(api_base_url: str, api_key: str) -> bool:
    client = TactoFlowClient(api_base_url, api_key)
    ok, _ = client.health()
    return ok


@st.cache_data(ttl=60, show_spinner="Carregando restaurantes…")
def _cached_restaurants(api_base_url: str, api_key: str) -> tuple[bool, Any]:
    client = TactoFlowClient(api_base_url, api_key)
    return client.list_restaurants()


@st.cache_data(ttl=60, show_spinner="Carregando instâncias…")
def _cached_instances(join_base_url: str, join_token: str) -> tuple[bool, Any]:
    client = JoinClient(join_base_url, join_token)
    return client.list_instances()


def _invalidate_caches() -> None:
    _cached_health.clear()
    _cached_restaurants.clear()
    _cached_instances.clear()
    st.session_state.pop("persona_cache", None)


def _persona_cache() -> dict[str, dict[str, Any]]:
    """Session cache: current agent_config (persona) per restaurant id."""
    if "persona_cache" not in st.session_state:
        st.session_state.persona_cache = {}
    return st.session_state.persona_cache


def _load_personas(tacto: TactoFlowClient, restaurant_ids: list[str]) -> None:
    """Fill the persona cache for the given restaurants.

    Stops after 2 consecutive failures so an unstable API doesn't hang the page.
    """
    cache = _persona_cache()
    failures = 0
    for rid in restaurant_ids:
        if rid in cache:
            continue
        ok, persona = tacto.get_restaurant_persona(rid)
        if ok:
            cache[rid] = persona
            failures = 0
        else:
            failures += 1
            if failures >= 2:
                break


st.set_page_config(
    page_title="Tacto Onboarding",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
:root {
    --tacto-primary: #ff4b4b;
    --tacto-primary-dark: #d92d20;
    --tacto-soft: #fff5f5;
    --tacto-ink: #101828;
    --tacto-ink-soft: #475467;
}
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1200px; }
h1, h2, h3 { font-family: "Inter", "Segoe UI", sans-serif; color: var(--tacto-ink); }
.stButton > button { border-radius: 10px; font-weight: 600; }
.stButton > button[kind="primary"] { background: var(--tacto-primary); }
[data-testid="stMetricValue"] { font-size: 1.6rem; }

/* ── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #eaecf0;
    min-width: 290px !important;
}
[data-testid="stSidebar"] > div { padding: 1.25rem 0.9rem; }
.sidebar-brand {
    background: transparent;
    border: none;
    padding: 0.4rem 0.5rem 0.8rem 0.5rem;
    text-align: center;
    margin-bottom: 0.4rem;
    box-shadow: none;
}
.sidebar-brand img {
    width: 70%;
    max-width: 170px;
    height: auto;
    display: inline-block;
}
.sidebar-brand .brand-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #d0d5dd, transparent);
    margin: 0.7rem 0 0.45rem 0;
}
.sidebar-brand .brand-caption {
    color: #475467 !important;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-weight: 600;
}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: var(--tacto-ink) !important;
}
[data-testid="stSidebar"] h2 {
    color: var(--tacto-primary-dark) !important;
    font-weight: 800;
    margin: 0 0 0.1rem 0;
    font-size: 1.6rem;
    letter-spacing: -0.02em;
}
.sidebar-subtitle {
    color: var(--tacto-ink-soft) !important;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}
.sidebar-section {
    text-transform: uppercase;
    color: var(--tacto-ink-soft) !important;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    font-weight: 700;
    margin: 0.8rem 0 0.4rem 0;
}
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 0.25rem;
}
[data-testid="stSidebar"] [role="radiogroup"] > label {
    background: #f9fafb;
    border: 1px solid #eaecf0;
    border-radius: 10px;
    padding: 0.55rem 0.75rem !important;
    font-size: 0.98rem;
    font-weight: 500;
    transition: background 0.12s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: #fff5f5;
    border-color: #fecdca;
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
    margin-right: 0.5rem;
}
.sidebar-status {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.6rem 0.85rem;
    border-radius: 10px;
    font-size: 0.9rem;
    font-weight: 600;
}
.sidebar-status .dot {
    width: 9px; height: 9px; border-radius: 50%;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.6);
}
.status-online  { background: #ecfdf3; color: #027a48; border: 1px solid #abefc6; }
.status-online .dot { background: #12b76a; }
.status-offline { background: #fef3f2; color: #b42318; border: 1px solid #fecdca; }
.status-offline .dot { background: #f04438; }
.sidebar-chip {
    display: inline-block;
    background: #f2f4f7;
    color: var(--tacto-ink-soft) !important;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    margin-top: 0.4rem;
}
.sidebar-footer {
    margin-top: 1rem;
    color: var(--tacto-ink-soft) !important;
    font-size: 0.72rem;
    text-align: center;
}
[data-testid="stSidebar"] .stButton > button {
    background: #ffffff !important;
    color: var(--tacto-ink) !important;
    border: 1px solid #d0d5dd !important;
    font-weight: 600;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #fff5f5 !important;
    border-color: var(--tacto-primary) !important;
    color: var(--tacto-primary-dark) !important;
}

/* ── Main content ──────────────────────────────── */
.tacto-pill {
    display: inline-block; padding: 0.15rem 0.65rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
}
.pill-on  { background: #d1fadf; color: #027a48; }
.pill-off { background: #fef0c7; color: #b54708; }
.tacto-card {
    border: 1px solid #eee; border-radius: 14px; padding: 1rem 1.25rem;
    background: #fff;
    box-shadow: 0 1px 2px rgba(16,24,40,0.05);
}
.tacto-muted { color: #8a94a6; font-size: 0.85rem; }
/* inherit = segue o tema do Streamlit: branco no escuro, escuro no claro */
.tacto-restaurant-name { font-size: 1.05rem; font-weight: 700; color: inherit; }
</style>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _pill(text: str, on: bool) -> str:
    cls = "pill-on" if on else "pill-off"
    return f'<span class="tacto-pill {cls}">{text}</span>'


def _is_connected(instance: dict[str, Any]) -> bool:
    return (instance.get("status") or "").lower() in {"open", "connected", "ativo"}


def _format_phone(raw: str | None) -> str:
    if not raw:
        return "—"
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 12:
        return f"+{digits[:2]} ({digits[2:4]}) {digits[4:9]}-{digits[9:]}"
    return raw


def _fold(text: str) -> str:
    """Lowercase + strip accents so 'goias' matches 'Goiás'."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text.lower())
        if not unicodedata.combining(ch)
    )


# ── Auth ──────────────────────────────────────────────────────────────────────


def _login_form(settings: Settings) -> None:
    remembered = _load_remembered()
    if (
        remembered.get("email") == settings.auth_email
        and remembered.get("password") == settings.auth_password
    ):
        st.session_state.authenticated = True
        st.rerun()

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("# Tacto Onboarding")
        st.caption("Painel interno para cadastrar restaurantes na plataforma.")
        with st.container(border=True):
            with st.form("login", clear_on_submit=False):
                email = st.text_input(
                    "E-mail",
                    value=remembered.get("email", ""),
                    placeholder="admin@tacto.local",
                )
                password = st.text_input(
                    "Senha",
                    value=remembered.get("password", ""),
                    type="password",
                )
                remember = st.checkbox(
                    "Lembrar e-mail e senha neste navegador", value=True
                )
                submitted = st.form_submit_button(
                    "Entrar", type="primary", use_container_width=True
                )
        if submitted:
            if email == settings.auth_email and password == settings.auth_password:
                if remember:
                    _save_remembered(email, password)
                else:
                    _clear_remembered()
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")


# ── Sidebar ───────────────────────────────────────────────────────────────────


def _sidebar(settings: Settings, tacto: TactoFlowClient) -> str:
    with st.sidebar:
        logo = _logo_data_uri()
        if logo:
            st.markdown(
                f"""
                <div class="sidebar-brand">
                    <img src="{logo}" alt="Tacto" />
                    <div class="brand-divider"></div>
                    <div class="brand-caption">Painel de Onboarding</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown("## Tacto")
            st.markdown(
                '<div class="sidebar-subtitle">Painel de onboarding</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sidebar-section">Navegar</div>', unsafe_allow_html=True)
        page = st.radio(
            "Menu",
            ["Novo restaurante", "Restaurantes", "WhatsApp"],
            label_visibility="collapsed",
        )

        st.markdown('<div class="sidebar-section">Status</div>', unsafe_allow_html=True)
        ok = _cached_health(settings.api_base_url, settings.api_key)
        if ok:
            st.markdown(
                '<div class="sidebar-status status-online">'
                '<span class="dot"></span> API online</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="sidebar-status status-offline">'
                '<span class="dot"></span> API indisponível</div>',
                unsafe_allow_html=True,
            )
        host = settings.api_base_url.replace("https://", "").replace("http://", "")
        st.markdown(
            f'<span class="sidebar-chip">{host}</span>', unsafe_allow_html=True
        )

        st.markdown('<div class="sidebar-section">Sessão</div>', unsafe_allow_html=True)
        if st.button("Sair", use_container_width=True):
            _clear_remembered()
            st.session_state.clear()
            st.rerun()

        st.markdown(
            '<div class="sidebar-footer">Tacto Onboarding · v0.1</div>',
            unsafe_allow_html=True,
        )

    return page


# ── Page: Novo restaurante ────────────────────────────────────────────────────


def _render_cadastrar(tacto: TactoFlowClient, join: JoinClient) -> None:
    st.markdown("## Cadastrar novo restaurante")
    st.caption(
        "Cria a instância Join, registra o restaurante e sincroniza o cardápio "
        "Tacto em uma única operação."
    )

    with st.container(border=True):
        with st.form("cadastrar", clear_on_submit=False):
            st.markdown("#### Dados do restaurante")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Nome do restaurante",
                    placeholder="Frutos de Goias",
                )
                attendant_name = st.text_input(
                    "Apelido do atendente",
                    value="",
                    placeholder="escolha qualquer nome — vazio usa Maria (fem.) / José (masc.)",
                    help=(
                        "Como o assistente se apresentará no WhatsApp. Escolha "
                        "qualquer nome; se deixar vazio, usa o padrão do gênero "
                        "escolhido abaixo: Maria (feminino) ou José (masculino)."
                    ),
                )
            with col2:
                menu_url = st.text_input(
                    "Link WebGula",
                    placeholder="https://v2.webgula.com.br/.../delivery",
                )
                canal_master_id = st.text_input(
                    "Chave Join",
                    placeholder="wp-empresa-708",
                    help="Identificador da instância WhatsApp na Join Developer.",
                )

            st.markdown("#### Identificação Tacto")
            col3, col4 = st.columns(2)
            with col3:
                chave_grupo = st.text_input(
                    "Chave Empresarial",
                    placeholder="52885ECC-696D-4BB9-9C83-EF9E0CB7FE4D",
                    help="UUID do grupo empresarial fornecido pela Tacto.",
                )
            with col4:
                empresa_base_id = st.text_input(
                    "Empresa Base",
                    placeholder="3",
                    help="ID numérico da empresa dentro do grupo.",
                )

            with st.expander("Personalidade do atendente (opcional)", expanded=False):
                st.caption(
                    "Ajuste como o assistente conversa no WhatsApp. "
                    "Os valores abaixo são os padrões da plataforma."
                )
                pc1, pc2, pc3 = st.columns(3)
                attendant_gender = pc1.selectbox(
                    "Gênero",
                    ["feminino", "masculino", "neutro"],
                    index=0,
                    help="Define artigos e pronomes (a/o atendente).",
                )
                persona_style = pc2.selectbox(
                    "Estilo",
                    ["formal", "informal"],
                    index=0,
                    help="Formal usa “senhor/senhora” e linguagem mais polida. "
                         "Informal é mais próximo e descontraído.",
                )
                max_emojis = pc3.slider(
                    "Emojis por mensagem",
                    min_value=0, max_value=5, value=1, step=1,
                    help="0 = nunca usar emoji. 5 = livre.",
                )

            st.write("")
            cols = st.columns([1, 1, 1])
            only_join = cols[0].form_submit_button(
                "Conectar Join (somente)", use_container_width=True
            )
            only_restaurant = cols[1].form_submit_button(
                "Cadastrar Restaurante", use_container_width=True
            )
            submitted = cols[2].form_submit_button(
                "Cadastrar Restaurante e Join",
                type="primary",
                use_container_width=True,
            )

    if only_join:
        _handle_only_join(join, canal_master_id)
        return

    if only_restaurant:
        _handle_full_onboarding(
            tacto,
            join,
            name=name,
            menu_url=menu_url,
            chave_grupo=chave_grupo,
            canal_master_id=canal_master_id,
            empresa_base_id=empresa_base_id,
            attendant_name=attendant_name,
            attendant_gender=attendant_gender,
            persona_style=persona_style,
            max_emojis=max_emojis,
            create_join=False,
        )
        return

    if submitted:
        _handle_full_onboarding(
            tacto,
            join,
            name=name,
            menu_url=menu_url,
            chave_grupo=chave_grupo,
            canal_master_id=canal_master_id,
            empresa_base_id=empresa_base_id,
            attendant_name=attendant_name,
            attendant_gender=attendant_gender,
            persona_style=persona_style,
            max_emojis=max_emojis,
            create_join=True,
        )


def _handle_only_join(join: JoinClient, canal_master_id: str) -> None:
    if not canal_master_id.strip():
        st.error("Informe a Chave Join para criar a instância.")
        return
    with st.status("Criando instância Join…", expanded=True) as status:
        ok, payload = join.create_instance(canal_master_id.strip())
        if ok:
            status.update(label="Instância criada.", state="complete")
            st.success(f"Instância **{canal_master_id}** criada com sucesso.")
            st.info("Cliente deve conectar o WhatsApp pelo painel Tacto.")
        elif "já existe" in str(payload).lower() or "existe uma instância" in str(payload).lower():
            status.update(label="Instância já existente", state="complete")
            st.info(f"Instância **{canal_master_id}** já estava criada.")
        else:
            status.update(label="Falha ao criar instância", state="error")
            st.error(payload)


def _handle_full_onboarding(
    tacto: TactoFlowClient,
    join: JoinClient,
    *,
    name: str,
    menu_url: str,
    chave_grupo: str,
    canal_master_id: str,
    empresa_base_id: str,
    attendant_name: str,
    attendant_gender: str,
    persona_style: str,
    max_emojis: int,
    create_join: bool = True,
) -> None:
    missing = [
        label
        for label, value in [
            ("Nome", name),
            ("Chave Empresarial", chave_grupo),
            ("Empresa Base", empresa_base_id),
            ("Chave Join", canal_master_id),
            ("Link WebGula", menu_url),
        ]
        if not value.strip()
    ]
    if missing:
        st.error(f"Preencha: {', '.join(missing)}")
        return

    title = "Executando onboarding…" if create_join else "Cadastrando restaurante…"
    with st.status(title, expanded=True) as status:
        step = 1
        if create_join:
            st.write(f"**{step}.** Criando instância Join…")
            ok, payload = join.create_instance(canal_master_id.strip())
            if ok:
                st.success(f"Instância `{canal_master_id}` criada.")
            elif "já existe" in str(payload).lower() or "existe uma instância" in str(payload).lower():
                st.info(f"Instância `{canal_master_id}` já existia.")
            else:
                status.update(label="Falha ao criar instância Join", state="error")
                st.error(payload)
                return
            step += 1

        st.write(f"**{step}.** Registrando restaurante…")
        ok, payload = tacto.create_restaurant(
            name=name.strip(),
            menu_url=menu_url.strip(),
            chave_grupo_empresarial=chave_grupo.strip(),
            canal_master_id=canal_master_id.strip(),
            empresa_base_id=empresa_base_id.strip(),
            attendant_name=attendant_name.strip() or None,
            attendant_gender=attendant_gender,
            persona_style=persona_style,
            max_emojis_per_message=max_emojis,
        )
        if not ok:
            status.update(label="Falha ao criar restaurante", state="error")
            st.error(payload)
            return
        restaurant_id = payload["id"]
        _cached_restaurants.clear()
        st.success("Restaurante criado.")
        step += 1

        st.write(f"**{step}.** Sincronizando cardápio + embeddings…")
        ok, sync = tacto.tacto_sync(restaurant_id)
        if not ok:
            status.update(label="Restaurante criado, sync falhou", state="error")
            st.error(sync)
            return
        status.update(label="Cadastro concluído.", state="complete")

    st.markdown("### Resumo")
    c1, c2, c3 = st.columns(3)
    c1.metric("Itens sincronizados", sync["items_synced"])
    c2.metric("Categorias", len(sync["categories"]))
    c3.metric("Status", "Pronto")
    with st.expander("Detalhes", expanded=False):
        st.markdown(f"**Endereço:** {sync.get('address') or '—'}")
        st.markdown("**Horários:**")
        st.code(sync.get("hours_text") or "—", language=None)
        st.markdown("**Categorias:** " + ", ".join(sync["categories"]))


# ── Page: Restaurantes ────────────────────────────────────────────────────────


def _connect_join_for_restaurant(
    join: JoinClient, canal_master_id: str, webhook_url: str
) -> tuple[bool, str]:
    """Configure the Join webhook URL for an instance already provisioned elsewhere.

    Instance creation and QR-code scanning happen in the external Tacto panel —
    this dashboard only links an existing instance to our webhook so messages
    are routed to the AI pipeline. The Join webhook endpoint is idempotent;
    re-clicking just overwrites the URL.
    """
    last_err: str = ""
    for _ in range(3):
        ok, payload = join.configure_webhook(canal_master_id, webhook_url)
        if ok:
            return True, f"Webhook configurado: {webhook_url}"
        last_err = str(payload)
        time.sleep(2)
    return False, f"Webhook não configurou: {last_err}"


_AUTOMATION_LABELS = {1: "1 — BASIC", 2: "2 — INTERMEDIATE", 3: "3 — ADVANCED"}
_INTEGRATION_LABELS = {1: "1 — Tacto", 2: "2 — JOIN"}
_GENDER_OPTIONS = ["(default plataforma)", "feminino", "masculino", "neutro"]
_STYLE_OPTIONS = ["(default plataforma)", "formal", "informal"]


def _default_attendant_for(persona: dict[str, Any]) -> str:
    """Gender-based default name shown when the restaurant has no override."""
    return "José" if persona.get("attendant_gender") == "masculino" else "Maria"


def _save_attendant_name(tacto: TactoFlowClient, rid: str, name: str | None) -> None:
    """Update only the attendant name, preserving all other persona overrides.

    Re-reads the current persona right before writing (read-merge-write) so a
    partial update can never wipe gender/style/emoji overrides.
    """
    ok, current = tacto.get_restaurant_persona(rid)
    if not ok:
        st.error(f"Não foi possível ler a persona atual — nada foi alterado. ({current})")
        return
    new_config = dict(current)
    if name:
        new_config["attendant_name"] = name
    else:
        new_config.pop("attendant_name", None)
    with st.spinner("Salvando…"):
        ok, payload = tacto.update_restaurant(rid, agent_config=new_config)
    if not ok:
        st.error(payload)
        return
    updated = payload.get("agent_config") if isinstance(payload, dict) else None
    _persona_cache()[rid] = updated or {}
    st.session_state.pop(f"qe-name-{rid}", None)
    st.toast("Atendente atualizada.", icon="✅")
    st.rerun()


def _render_attendant_quick_edit(tacto: TactoFlowClient, r: dict[str, Any]) -> None:
    """Compact popover to view/change the attendant name in two clicks."""
    rid = r["id"]
    persona = _persona_cache().get(rid) or {}
    current_name = (persona.get("attendant_name") or "").strip()

    with st.popover("✏️ Atendente", use_container_width=True):
        st.caption(
            f"Nome atual: **{current_name}**"
            if current_name
            else f"Nome atual: *padrão — {_default_attendant_for(persona)}*"
        )
        new_name = st.text_input(
            "Novo nome da atendente",
            value=current_name,
            key=f"qe-name-{rid}",
            placeholder="ex: Julia",
        )
        col_save, col_default = st.columns(2)
        if col_save.button(
            "Salvar", key=f"qe-save-{rid}", type="primary", use_container_width=True
        ):
            candidate = new_name.strip()
            if len(candidate) < 2:
                st.error("O nome precisa de pelo menos 2 caracteres.")
            elif candidate == current_name:
                st.info("O nome já é esse.")
            else:
                _save_attendant_name(tacto, rid, candidate)
        if col_default.button(
            "Usar padrão",
            key=f"qe-clear-{rid}",
            use_container_width=True,
            help="Remove o nome customizado — o bot volta ao padrão da plataforma.",
        ):
            _save_attendant_name(tacto, rid, None)


def _render_edit_restaurant_form(tacto: TactoFlowClient, r: dict[str, Any]) -> None:
    """Render an inline edit form for a restaurant inside its card."""
    rid = r["id"]
    current_auto = int(r["automation_type"])
    current_int = int(r["integration_type"])
    current_active = bool(r["is_active"])
    # Current persona comes from the session cache (no-op PATCH read) because
    # the deployed backend returns agent_config empty on the list endpoint.
    persona_cached = _persona_cache().get(rid)
    persona_known = persona_cached is not None
    ac = persona_cached or {}
    current_att_name = ac.get("attendant_name") or ""
    current_att_gender = ac.get("attendant_gender") or "(default plataforma)"
    current_style = ac.get("persona_style") or "(default plataforma)"
    current_emoji = ac.get("max_emojis_per_message")
    emoji_use_default = current_emoji is None

    with st.expander("Editar restaurante", expanded=False):
        with st.form(f"edit-form-{rid}", clear_on_submit=False):
            col_a, col_b = st.columns(2)
            new_name = col_a.text_input("Nome", value=r["name"], key=f"edit-name-{rid}")
            new_menu_url = col_b.text_input("URL Webgula", value=r["menu_url"], key=f"edit-url-{rid}")

            col_c, col_d, col_e = st.columns([1.2, 1.2, 1])
            new_automation = col_c.selectbox(
                "Automação",
                options=[1, 2, 3],
                index=[1, 2, 3].index(current_auto),
                format_func=lambda x: _AUTOMATION_LABELS[x],
                key=f"edit-auto-{rid}",
            )
            new_integration = col_d.selectbox(
                "Integração",
                options=[1, 2],
                index=[1, 2].index(current_int),
                format_func=lambda x: _INTEGRATION_LABELS[x],
                key=f"edit-int-{rid}",
            )
            new_active = col_e.toggle("Ativo", value=current_active, key=f"edit-active-{rid}")

            new_timezone = st.text_input(
                "Fuso horário (IANA)",
                value=r.get("timezone", "") or "",
                key=f"edit-tz-{rid}",
                help="Ex: America/Sao_Paulo. Preenchido automaticamente pelo estado (UF) no tacto-sync.",
            )

            st.markdown("**Persona do atendente** — deixe em *(default plataforma)* para usar o padrão global.")
            pcol_a, pcol_b = st.columns(2)
            new_att_name = pcol_a.text_input(
                "Nome do atendente",
                value=current_att_name,
                key=f"edit-att-name-{rid}",
                placeholder="ex: Maria",
            )
            new_att_gender = pcol_b.selectbox(
                "Gênero gramatical",
                options=_GENDER_OPTIONS,
                index=_GENDER_OPTIONS.index(current_att_gender),
                key=f"edit-att-gender-{rid}",
            )
            pcol_c, pcol_d = st.columns(2)
            new_style = pcol_c.selectbox(
                "Estilo",
                options=_STYLE_OPTIONS,
                index=_STYLE_OPTIONS.index(current_style),
                key=f"edit-style-{rid}",
            )
            emoji_default_toggle = pcol_d.checkbox(
                "Máx emojis: usar default da plataforma",
                value=emoji_use_default,
                key=f"edit-emoji-default-{rid}",
            )
            new_emoji_value = pcol_d.number_input(
                "Máx emojis por mensagem",
                min_value=0,
                max_value=5,
                value=int(current_emoji) if current_emoji is not None else 1,
                key=f"edit-emoji-{rid}",
                disabled=emoji_default_toggle,
            )

            new_prompt = st.text_area(
                "Prompt default (instruções customizadas para a IA — opcional)",
                value=r.get("prompt_default", "") or "",
                key=f"edit-prompt-{rid}",
                height=120,
            )

            bcol1, bcol2 = st.columns([1, 1])
            save_clicked = bcol1.form_submit_button(
                "Salvar alterações", use_container_width=True, type="primary"
            )
            clear_clicked = bcol2.form_submit_button(
                "Limpar persona (usar defaults)", use_container_width=True
            )

            if not (save_clicked or clear_clicked):
                return

            payload_kwargs: dict[str, Any] = {}
            if new_name.strip() and new_name.strip() != r["name"]:
                payload_kwargs["name"] = new_name.strip()
            if new_menu_url.strip() and new_menu_url.strip() != r["menu_url"]:
                payload_kwargs["menu_url"] = new_menu_url.strip()
            if new_automation != current_auto:
                payload_kwargs["automation_type"] = int(new_automation)
            if new_integration != current_int:
                payload_kwargs["integration_type"] = int(new_integration)
            if new_active != current_active:
                payload_kwargs["is_active"] = bool(new_active)
            if (new_prompt or "") != (r.get("prompt_default") or ""):
                payload_kwargs["prompt_default"] = new_prompt
            if new_timezone.strip() and new_timezone.strip() != (r.get("timezone") or ""):
                payload_kwargs["timezone"] = new_timezone.strip()

            if clear_clicked:
                payload_kwargs["agent_config"] = {}
            elif save_clicked:
                if not persona_known:
                    st.warning(
                        "Persona atual não carregada — os campos de persona não foram "
                        "enviados para evitar sobrescrever configurações. "
                        "Recarregue a página e tente novamente."
                    )
                else:
                    persona: dict[str, Any] = {}
                    if new_att_name.strip():
                        persona["attendant_name"] = new_att_name.strip()
                    if new_att_gender != "(default plataforma)":
                        persona["attendant_gender"] = new_att_gender
                    if new_style != "(default plataforma)":
                        persona["persona_style"] = new_style
                    if not emoji_default_toggle:
                        persona["max_emojis_per_message"] = int(new_emoji_value)
                    if persona != ac:
                        payload_kwargs["agent_config"] = persona

            if not payload_kwargs:
                st.info("Nenhuma alteração detectada.")
                return

            with st.spinner("Salvando…"):
                ok, payload = tacto.update_restaurant(rid, **payload_kwargs)

            if ok:
                _cached_restaurants.clear()
                st.success("Restaurante atualizado.")
                st.rerun()
            else:
                st.error(payload)


def _render_restaurantes(tacto: TactoFlowClient, join: JoinClient, settings: Settings) -> None:
    st.markdown("## Restaurantes")
    head_l, head_r = st.columns([5, 1])
    head_l.caption("Restaurantes ativos na plataforma. Use a busca pelo nome.")
    if head_r.button("Atualizar", key="refresh-restaurants", use_container_width=True):
        _cached_restaurants.clear()
        st.session_state.pop("persona_cache", None)
        st.rerun()

    ok, payload = _cached_restaurants(settings.api_base_url, settings.api_key)
    if not ok:
        st.error(payload)
        return

    items = payload.get("items", []) if isinstance(payload, dict) else []
    items_sorted = sorted(items, key=lambda r: r["name"].lower())

    cache = _persona_cache()
    if any(r["id"] not in cache for r in items_sorted):
        with st.spinner("Carregando atendentes atuais…"):
            _load_personas(tacto, [r["id"] for r in items_sorted])

    c1, c2 = st.columns([3, 1])
    with c1:
        if st_keyup is not None:
            raw_query = st_keyup(
                "Buscar",
                key="rest-search",
                debounce=250,
                placeholder="Buscar por nome, atendente ou wp-empresa…",
                label_visibility="collapsed",
            )
        else:
            raw_query = st.text_input(
                "Buscar",
                placeholder="Buscar por nome, atendente ou wp-empresa…",
                label_visibility="collapsed",
                help="Digite e pressione Enter para filtrar.",
            )
    query = _fold((raw_query or "").strip())

    def _matches(r: dict[str, Any]) -> bool:
        persona = _persona_cache().get(r["id"]) or {}
        haystack = _fold(
            f'{r["name"]} {r["canal_master_id"]} {persona.get("attendant_name") or ""}'
        )
        return query in haystack

    filtered = [r for r in items_sorted if _matches(r)] if query else items_sorted
    c2.metric("Exibindo", f"{len(filtered)}/{len(items_sorted)}")

    if not filtered:
        st.info("Nenhum restaurante encontrado.")
        return

    for r in filtered:
        with st.container(border=True):
            head_cols = st.columns([3.0, 1.3, 1.3, 1.3])
            head_cols[0].markdown(
                f'<div class="tacto-restaurant-name">{r["name"]}</div>',
                unsafe_allow_html=True,
            )
            head_cols[0].markdown(
                f'<div class="tacto-muted">WhatsApp: <code>{r["canal_master_id"]}</code> · Empresa Base: <code>{r["empresa_base_id"]}</code></div>',
                unsafe_allow_html=True,
            )
            persona = _persona_cache().get(r["id"])
            if persona is None:
                att_html = '<span class="tacto-muted">🎙️ Atendente: não carregada — clique em Atualizar</span>'
            elif persona.get("attendant_name"):
                att_html = f'🎙️ Atendente: <b>{persona["attendant_name"]}</b>'
            else:
                att_html = (
                    f'🎙️ Atendente: <b>{_default_attendant_for(persona)}</b> '
                    '<span class="tacto-muted">(padrão)</span>'
                )
            head_cols[0].markdown(
                f'<div style="margin-top:.15rem">{att_html}</div>',
                unsafe_allow_html=True,
            )
            with head_cols[1]:
                _render_attendant_quick_edit(tacto, r)
            if head_cols[2].button("Conectar Join", key=f"join-{r['id']}", use_container_width=True):
                with st.spinner(f"Conectando {r['name']} à Join…"):
                    ok, msg = _connect_join_for_restaurant(
                        join, r["canal_master_id"], settings.webhook_url
                    )
                if ok:
                    st.success(f"{r['name']}: {msg}")
                else:
                    st.error(msg)
            if head_cols[3].button("Re-sync cardápio", key=f"sync-{r['id']}", use_container_width=True):
                with st.spinner(f"Sincronizando {r['name']}…"):
                    ok, sync = tacto.tacto_sync(r["id"])
                if ok:
                    _cached_restaurants.clear()
                    st.success(
                        f"{sync['items_synced']} itens · {len(sync['categories'])} categorias."
                    )
                else:
                    st.error(sync)

            _render_edit_restaurant_form(tacto, r)

            with st.expander("Detalhes técnicos", expanded=False):
                st.markdown(
                    f"- **ID interno:** `{r['id']}`\n"
                    f"- **Chave Empresarial:** `{r['chave_grupo_empresarial']}`\n"
                    f"- **Cardápio:** [{r['menu_url']}]({r['menu_url']})\n"
                    f"- **Automação:** tipo {r['automation_type']} · "
                    f"**Integração:** tipo {r['integration_type']}"
                )


# ── Page: WhatsApp ────────────────────────────────────────────────────────────


def _render_instancias(join: JoinClient, settings: Settings) -> None:
    st.markdown("## Instâncias WhatsApp")
    st.caption(
        "Status de conexão de cada instância Join. O webhook só pode ser "
        "configurado depois que o cliente escaneia o QR pela plataforma Tacto."
    )

    if st.button("Atualizar lista", key="refresh-instances"):
        _cached_instances.clear()
        st.rerun()

    ok, instances = _cached_instances(settings.join_api_base_url, settings.join_token_cliente)
    if not ok:
        st.error(instances)
        return

    connected = [i for i in instances if _is_connected(i)]
    pending = [i for i in instances if not _is_connected(i)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", len(instances))
    c2.metric("Conectadas", len(connected))
    c3.metric("Aguardando QR", len(pending))

    query = st.text_input(
        "Buscar pelo nome",
        placeholder="ex: wp-empresa-708",
        label_visibility="collapsed",
    ).strip().lower()

    filtered = (
        [i for i in instances if query in (i.get("nome") or "").lower()]
        if query
        else instances
    )
    filtered = sorted(filtered, key=lambda i: (not _is_connected(i), i.get("nome") or ""))

    if not filtered:
        st.info("Nenhuma instância encontrada.")
        return

    for inst in filtered:
        nome = inst.get("nome") or "?"
        phone = _format_phone(inst.get("numero_conectado"))
        is_on = _is_connected(inst)
        with st.container(border=True):
            cols = st.columns([3, 2, 2])
            cols[0].markdown(
                f'<div class="tacto-restaurant-name">{nome}</div>',
                unsafe_allow_html=True,
            )
            cols[0].markdown(
                _pill("Conectada" if is_on else "Aguardando QR", is_on),
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                f'<div class="tacto-muted">WhatsApp</div><div>{phone}</div>',
                unsafe_allow_html=True,
            )
            if is_on:
                if cols[2].button("Configurar webhook", key=f"wh-{nome}", use_container_width=True):
                    with st.spinner("Configurando…"):
                        ok, payload = join.configure_webhook(nome, settings.webhook_url)
                    if ok:
                        st.success(f"Webhook configurado para **{nome}**.")
                    else:
                        st.error(payload)
            else:
                cols[2].markdown(
                    '<div class="tacto-muted" style="text-align:right; padding-top:.6rem">'
                    "Cliente conecta pelo painel Tacto</div>",
                    unsafe_allow_html=True,
                )


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    try:
        settings = get_settings()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    if not st.session_state.get("authenticated"):
        _login_form(settings)
        return

    tacto = TactoFlowClient(settings.api_base_url, settings.api_key)
    join = JoinClient(settings.join_api_base_url, settings.join_token_cliente)

    page = _sidebar(settings, tacto)
    if page == "Novo restaurante":
        _render_cadastrar(tacto, join)
    elif page == "Restaurantes":
        _render_restaurantes(tacto, join, settings)
    elif page == "WhatsApp":
        _render_instancias(join, settings)


if __name__ == "__main__":
    main()
