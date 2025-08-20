import streamlit as st
import pandas as pd
import re, os, json
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Programação Semanal", page_icon="🛣️", layout="wide")

# ------------------------------ CONFIG BÁSICA ------------------------------
PASSWORD = "Ecovias123"
DATA_DIR = Path("data")
BASE_FILE = DATA_DIR / "base_atual.csv"
STATUS_FILE = DATA_DIR / "status.json"
DATA_DIR.mkdir(exist_ok=True)

# ------------------------------ FUNÇÕES AUX ------------------------------
def split_trecho_to_kms(trecho: str):
    # Divide 'NNN+MMM - NNN+MMM' em (disp_ini, disp_fim, num_ini, num_fim).
    if pd.isna(trecho):
        return None, None, None, None
    s = str(trecho)
    parts = s.split("-")
    if len(parts) == 2:
        left = parts[0].strip()
        right = parts[1].strip()
    else:
        left = s.strip()
        right = s.strip()

    def _parse_km_token(token: str):
        if token is None:
            return None, None
        t = str(token).strip()
        m = re.match(r"^\s*(\d+)\s*\+\s*(\d+)\s*$", t)
        if m:
            km = int(m.group(1)); mtrs = int(m.group(2))
            disp = f"{km:03d}+{mtrs:03d}"
            val = km + mtrs/1000.0
            return disp, val
        # fallback: número decimal -> gerar NNN+MMM
        t2 = t.replace(",", ".")
        try:
            val = float(t2)
            k = int(val); mm = int(round((val - k)*1000))
            disp = f"{k:03d}+{mm:03d}"
            return disp, val
        except:
            return t, None

    disp_ini, num_ini = _parse_km_token(left)
    disp_fim, num_fim = _parse_km_token(right)
    return disp_ini, disp_fim, num_ini, num_fim

def publish_base(df: pd.DataFrame, filename: str):
    # Remove arquivos antigos (apaga tudo dentro de data/)
    for p in DATA_DIR.glob("*"):
        try:
            p.unlink()
        except:
            pass
    # Salva CSV normalizado
    df.to_csv(BASE_FILE, index=False, encoding="utf-8")
    status = {
        "filename": filename,
        "rows": int(len(df)),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

def get_status():
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except:
        return None

def get_current_base():
    if BASE_FILE.exists():
        return pd.read_csv(BASE_FILE, parse_dates=["Inicio","DataFim"], dayfirst=True)
    return None

# ------------------------------ SIDEBAR ------------------------------
st.sidebar.title("🧭 Navegação")
page = st.sidebar.radio("Ir para", ["🔎 Buscar Programação", "🧹 Upload da Base"], label_visibility="collapsed")

status = get_status()
if status:
    st.sidebar.info(f"**Base atual:** {status.get('filename','-')}\n"
                    f"**Linhas:** {status.get('rows','-')}\n"
                    f"**Atualizado em:** {status.get('updated_at','-')}")
else:
    st.sidebar.warning("Nenhuma base publicada ainda.")

# ------------------------------ PÁGINAS ------------------------------
if page == "🧹 Upload da Base":
    st.header("🧹 Upload da Base")
    senha = st.text_input("Digite a senha para liberar o upload", type="password")
    if senha == PASSWORD:
        uploaded = st.file_uploader("Escolha a planilha (.xls ou .xlsx) - aba 'Dados'", type=["xls","xlsx"])
        if uploaded is not None:
            try:
                ext = uploaded.name.lower().split(".")[-1]
                if ext == "xls":
                    df_raw = pd.read_excel(uploaded, engine="xlrd")
                else:
                    df_raw = pd.read_excel(uploaded, engine="openpyxl")

                expected = ["Num Interv","Rodovia","Tipo","Inicio","DataFim","Sentido","Trecho"]
                missing = [c for c in expected if c not in df_raw.columns]
                if missing:
                    st.error(f"As seguintes colunas obrigatórias não foram encontradas: {missing}")
                else:
                    st.success(f"Arquivo '{uploaded.name}' lido com {len(df_raw)} linhas e {len(df_raw.columns)} colunas.")
                    st.dataframe(df_raw.head(15), use_container_width=True)
                    if st.button("Publicar base", type="primary"):
                        publish_base(df_raw, uploaded.name)
                        st.success("Base publicada com sucesso!")
                        st.balloons()
            except Exception as e:
                st.error(f"Erro ao ler a planilha: {e}")
    else:
        if senha != "":
            st.error("Senha incorreta. Tente novamente.")
        st.info("Informe a senha correta para habilitar o upload.")

else:
    st.title("🔎 Buscar Programação")
    df = get_current_base()
    if df is None or df.empty:
        st.warning("Nenhuma base publicada. Vá em **🧹 Upload da Base** na barra lateral.")
        st.stop()

    # Derivados
    df["Data"] = pd.to_datetime(df["Inicio"]).dt.date
    df["Hora"] = pd.to_datetime(df["Inicio"]).dt.time
    df["Periodo"] = df["Hora"].apply(lambda h: "Diurno" if getattr(h, "hour", None)==7 else ("Noturno" if getattr(h, "hour", None)==22 else "Outro"))
    kms = df["Trecho"].apply(split_trecho_to_kms)
    df["KM Inicial"] = kms.apply(lambda t: t[0])
    df["KM Final"]   = kms.apply(lambda t: t[1])
    df["KM_ini_num"] = kms.apply(lambda t: t[2])
    df["KM_fim_num"] = kms.apply(lambda t: t[3])

    # Filtros
    c1, c2, c3 = st.columns(3)
    with c1:
        rodovia = st.selectbox("Rodovia", sorted(df["Rodovia"].dropna().astype(str).unique()))
    with c2:
        tipo = st.selectbox("Tipo (Serviço)", sorted(df["Tipo"].dropna().astype(str).unique()))
    with c3:
        data_sel = st.date_input("Data (de Início)", value=df["Data"].min())

    c4, c5 = st.columns(2)
    with c4:
        periodo = st.selectbox("Período", ["Todos","Diurno","Noturno"])
    with c5:
        sentidos = ["(qualquer)"] + sorted([s for s in df["Sentido"].dropna().astype(str).unique() if s.strip()!=""])
        sentido = st.selectbox("Sentido", sentidos)

    exec_values = sorted([e for e in df["Executor"].dropna().astype(str).unique() if e.strip()!=""]) if "Executor" in df.columns else []
    executor_sel = st.multiselect("Executor (opcional, múltiplos)", exec_values, default=[])

    buscar = st.button("Buscar", type="primary")

    if buscar:
        f = df.copy()
        f = f[(f["Rodovia"].astype(str)==rodovia) & (f["Tipo"].astype(str)==tipo) & (f["Data"]==data_sel)]
        if periodo!="Todos":
            f = f[f["Periodo"]==periodo]
        if sentido!="(qualquer)":
            f = f[f["Sentido"].astype(str)==sentido]
        if executor_sel:
            f = f[f["Executor"].astype(str).isin(executor_sel)]

        f = f.sort_values(["Rodovia","KM_ini_num","KM_fim_num","Sentido","Inicio"], na_position="last")

        if f.empty:
            st.error("Nenhum registro encontrado para os filtros informados.")
        else:
            st.subheader("Números de Programação encontrados")
            nums = f["Num Interv"].astype(str).tolist()
            st.code("\n".join(nums))

            cols = ["Num Interv","Rodovia","KM Inicial","KM Final","Sentido","Tipo"]
            if "Executor" in f.columns:
                cols.append("Executor")
            cols += ["Inicio","DataFim"]
            cols = [c for c in cols if c in f.columns]
            st.dataframe(f[cols], use_container_width=True, hide_index=True)
