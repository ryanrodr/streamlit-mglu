import pandas as pd
import streamlit as st
import json
import gspread
import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
import sqlite3

# Carrega variáveis de ambiente com load_dotenv
load_dotenv()
KEY_JSON = os.getenv('KEY_JSON')
USERNAME_KEY = os.getenv('USERNAME_KEY')
PASSWORD_KEY = os.getenv('PASSWORD_KEY')

# Autenticação com Google Sheets
google_client = gspread.service_account_from_dict(json.loads(KEY_JSON))
SHEET_ID = '1tbJh_GQol0Ax5uB-AjwI26yW9piCIp0peuKV1N5nMeQ'
spreadsheet = google_client.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet('db')

# Configurações iniciais do aplicativo
st.sidebar.title("Navegação")
page = st.sidebar.radio("Escolha a página", ["Check-in Motoristas", "Visualização de Registros"])

# Função para criar a tabela no banco de dados SQLite
def database():
    conn = sqlite3.connect('dados_motoristas2.db')
    c = conn.cursor()
    
    # Cria a tabela se não existir
    c.execute('''CREATE TABLE IF NOT EXISTS motoristas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unidade TEXT,
                    nome TEXT,
                    placa TEXT,
                    chegada_cd TEXT,
                    inicio_carregamento TEXT,
                    fim_carregamento TEXT,
                    quantidade_remessas INTEGER
                )''')
    conn.commit()
    conn.close()

def salvar_database(data):
    conn = sqlite3.connect('dados_motoristas2.db')
    c = conn.cursor()
    
    # Insere os dados no banco de dados
    c.execute('''INSERT INTO motoristas (unidade, nome, placa, chegada_cd, inicio_carregamento, fim_carregamento, quantidade_remessas) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (data['Unidade'], data['Nome'], 
               data['Placa'], data.get('Chegada CD', ''), 
               data.get('Início do Carregamento', ''), data.get('Fim do Carregamento', ''), 
               data.get('Quantidade Remessas', 0)))
    
    conn.commit()
    conn.close()

def dados_existentes(dados_motorista):
    try:
        existing_data = worksheet.get_all_records()
        df_existing = pd.DataFrame(existing_data)

        # Verifique se o DataFrame está vazio
        if df_existing.empty:
            st.warning("A planilha está vazia. Nenhum registro encontrado.")
            return False  # Se a planilha está vazia, consideramos que não existem dados

        # Verifique as colunas carregadas
        if 'Unidade' not in df_existing.columns or 'Nome' not in df_existing.columns or 'Placa' not in df_existing.columns:
            st.error("As colunas necessárias não estão disponíveis na planilha.")
            return True  # Para evitar duplicatas, retornar True se não conseguir acessar

        # Verificar se o registro já existe
        return df_existing[
            (df_existing['Unidade'] == dados_motorista['Unidade']) &
            (df_existing['Nome'] == dados_motorista['Nome']) &
            (df_existing['Placa'] == dados_motorista['Placa'])
        ].shape[0] > 0
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler os dados da planilha: {str(e)}")
        return True  # Retornar True para evitar que dados duplicados sejam enviados

def motoristas():
    st.title("Check-in de Motoristas")

    # Lista de filiais
    lista_filiais = [
        "HVGI - VILA GUILHERME", "HUDI - UBERLÂNDIA", "HRAO - RIBEIRÃO PRETO",
        "HPPB - PRESIDENTE PRUDENTE", "HPLH - PALHOÇA", "OSA LM - OSASCO",
        "HITJ - ITAJAÍ", "HBHZ - BETIM", "HRIO - RIO DE JANEIRO", 
        "HPOA - PORTO ALEGRE ( GRAVATAÍ)", "HLDB - LONDRINA", 
        "HJAB - JABOATÃO DOS GUARARAPES", "HSSA - SALVADOR", "HCWB - CURITIBA", 
        "HBSB - BRASILIA", "HGRU - GUARULHOS", "HFOR - FORTALEZA", 
        "HFCA - FRANCA", "HCPQ - CAMPINAS", "HBAU - BAURU", "HARU - ARAÇATUBA"
    ]

    # Seleção da etapa do check-in
    subpagina = st.selectbox("Escolha a etapa", ["Chegada CD", "Início do Carregamento", "Fim do Carregamento"])

    # Função para registrar o horário atual
    def registrar_horario():
        br_tz = pytz.timezone('America/Sao_Paulo')
        return datetime.now(br_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Step 1: Coleta de informações de chegada
    if subpagina == "Chegada CD":
        filial = st.selectbox("Filial", lista_filiais, index=0)
        nome = st.text_input("Nome do Motorista").upper()
        placa = st.text_input("Placa do Veículo", '').upper()

        if st.button("Check"):
            if not placa:  # Valida se a placa foi inserida
                st.error("Por favor, insira a placa do veículo.")
            else:
                chegada = registrar_horario()
                dados_motorista = {
                    'Unidade': filial,
                    'Nome': nome,
                    'Placa': placa,
                    'Chegada CD': chegada,
                    'Início do Carregamento': '',
                    'Fim do Carregamento': '',
                    'Quantidade Remessas': 0
                }
                salvar_database(dados_motorista)  # Salva no SQLite
                st.success(f"Horário de Chegada registrado: {chegada}")

    # Step 2: Coleta de informações de entrada no CD
    elif subpagina == "Início do Carregamento":
        placa = st.text_input("Placa do Veículo", '').upper()
        if st.button("Check"):
            if not placa:  # Valida se a placa foi inserida
                st.error("Por favor, insira a placa do veículo.")
            else:
                entrada_cd = registrar_horario()
                # Atualiza a entrada no SQLite
                conn = sqlite3.connect('dados_motoristas2.db')
                c = conn.cursor()
                c.execute('''UPDATE motoristas SET inicio_carregamento = ? WHERE placa = ?''', 
                          (entrada_cd, placa))
                conn.commit()
                conn.close()
                st.success(f"Horário de Entrada registrado: {entrada_cd}")

    # Step 3: Coleta de informações de saída do CD e quantidade de remessas
    elif subpagina == "Fim do Carregamento":
        placa = st.text_input("Placa do Veículo", '').upper()
        quantidade_remessas = st.number_input("Quantidade de Remessas", min_value=0, value=0)

        if st.button("Check"):
            if not placa:  # Valida se a placa foi inserida
                st.error("Por favor, insira a placa do veículo.")
            else:
                saida_cd = registrar_horario()
                # Atualiza a saída e quantidade de remessas no SQLite
                conn = sqlite3.connect('dados_motoristas2.db')
                c = conn.cursor()
                c.execute('''UPDATE motoristas SET fim_carregamento = ?, quantidade_remessas = ? WHERE placa = ?''', 
                          (saida_cd, quantidade_remessas, placa))
                conn.commit()
                conn.close()
                st.success(f"Horário de Saída registrado: {saida_cd}")
                st.success("Check-in registrado com sucesso!")

def registros_sqlite():
    conn = sqlite3.connect('dados_motoristas2.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM motoristas")
    registros = c.fetchall()
    
    conn.close()
    
    if registros:
        df = pd.DataFrame(registros, columns=['ID', 'Unidade', 'Nome', 'Placa', 'Chegada CD', 'Início do Carregamento', 'Fim do Carregamento', 'Quantidade Remessas'])
        df_unique = df.drop_duplicates(subset='Placa', keep='last')
        return df_unique
    else:
        return pd.DataFrame()

# Função para enviar dados em batch
def enviar_dados_em_batch(dados):
    batch_requests = []

    for index, registro in dados.iterrows():
        # Verifica se todos os campos estão preenchidos e se "Quantidade Remessas" é maior que 0
        if all(pd.notna(registro[1:])) and registro['Quantidade Remessas'] > 0:
            linha_dados = [
                registro['Unidade'], 
                registro['Nome'],
                registro['Placa'], 
                registro['Chegada CD'], 
                registro['Início do Carregamento'], 
                registro['Fim do Carregamento'], 
                registro['Quantidade Remessas']
            ]
            batch_requests.append(linha_dados)

    if batch_requests:
        worksheet.append_rows(batch_requests)
        print(f"{len(batch_requests)} registros enviados para o Google Sheets com sucesso!")
    else:
        print("Nenhum dado válido para enviar.")

# Função para visualizar os registros
def registros():
    st.title("Visualização de Registros")
    st.write("Os dados são atualizados em tempo real conforme o processo de check-in é concluído.")

    df_registros = registros_sqlite()

    if df_registros.empty:
        st.warning("Nenhum registro encontrado.")
        return

    unidades = df_registros['Unidade'].unique().tolist()
    unidade_selecionada = st.selectbox("Selecione a Unidade para filtrar", ["Todas"] + unidades)

    if unidade_selecionada != "Todas":
        df_registros = df_registros[df_registros['Unidade'] == unidade_selecionada]

    st.dataframe(df_registros)

    # Lista para armazenar dados que precisam ser enviados
    dados_para_enviar = []

    # Verifica e coleta dados para envio
    for index, registro in df_registros.iterrows():
        dados_motorista = {
            'Unidade': registro['Unidade'],
            'Nome': registro['Nome'],
            'Placa': registro['Placa'],
            'Chegada CD': registro['Chegada CD'],
            'Início do Carregamento': registro['Início do Carregamento'],
            'Fim do Carregamento': registro['Fim do Carregamento'],
            'Quantidade Remessas': registro['Quantidade Remessas']
        }

        if not dados_existentes(dados_motorista):
            dados_para_enviar.append(dados_motorista)
        else:
            st.warning(f"Registro já existente para a placa {registro['Placa']}. Não enviado.")

    if dados_para_enviar:
        enviar_dados_em_batch(pd.DataFrame(dados_para_enviar))
    else:
        st.warning("Nenhum dado válido para enviar.")

# Chama a função para criar a tabela ao iniciar o app
database()

# Função de Login
def login():
    st.title("Acesso Interno Magalu")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type='password')

    if st.button("Entrar"):
        if username == USERNAME_KEY and password == PASSWORD_KEY:
            st.session_state['authenticated'] = True
            st.success("Login bem-sucedido!")
        else:
            st.error("Usuário ou senha inválidos.")

# Função de Logout
def logout():
    st.session_state['authenticated'] = False
    st.success("Logout bem-sucedido!")

# Inicializa o estado da sessão
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Roteamento de páginas
if page == "Check-in Motoristas":
    motoristas()  # Função que lida com o check-in de motoristas
elif page in ["Visualização de Registros", "Relatório de Registros"]:
    # Verifica se o usuário está autenticado
    if st.session_state['authenticated']:
        if page == "Visualização de Registros":
            registros()  # Função para visualizar registros
    else:
        login()  # Se não autenticado, exibe a tela de login

# Adiciona um botão de logout na parte inferior
if st.session_state['authenticated']:
    if st.button("Sair"):
        logout()