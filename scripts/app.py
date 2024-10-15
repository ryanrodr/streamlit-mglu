import pandas as pd
import streamlit as st
import json
import gspread
import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
import sqlite3  # Importando SQLite

# Identificador único da planilha do Google Sheets
SHEET_ID = '1tbJh_GQol0Ax5uB-AjwI26yW9piCIp0peuKV1N5nMeQ'

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém a variável de ambiente KEY_JSON
key_json = os.getenv('KEY_JSON')

# Obter credenciais do arquivo .env
USERNAME_KEY = os.getenv('USERNAME_KEY')
PASSWORD_KEY = os.getenv('PASSWORD_KEY')

# Converte a string JSON em um dicionário Python
google_client = gspread.service_account_from_dict(json.loads(key_json))

# Abre a planilha do Google Sheets usando o código único da planilha
spreadsheet = google_client.open_by_key(SHEET_ID)

# Seleciona a aba chamada 'Dados' dentro da planilha
worksheet = spreadsheet.worksheet('Dados')

# Função para criar a tabela no banco de dados SQLite
def create_database():
    conn = sqlite3.connect('dados_motoristas.db')
    c = conn.cursor()
    
    # Cria a tabela se ela não existir, removendo o campo UUID
    c.execute('''CREATE TABLE IF NOT EXISTS motoristas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unidade TEXT,
                    motorista TEXT,
                    placa TEXT,
                    chegada_cd TEXT,
                    inicio_carregamento TEXT,
                    fim_carregamento TEXT,
                    quantidade_remessas INTEGER
                )''')
    conn.commit()
    conn.close()

def salvar_no_sqlite(data):
    conn = sqlite3.connect('dados_motoristas.db')
    c = conn.cursor()
    
    # Insere os dados no banco de dados
    c.execute('''INSERT INTO motoristas (unidade, motorista, placa, chegada_cd, inicio_carregamento, fim_carregamento, quantidade_remessas) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (data['Unidade'], data['Nome'], 
               data['Placa'], data.get('Chegada CD', ''), 
               data.get('Início do Carregamento', ''), data.get('Fim do Carregamento', ''), 
               data.get('Quantidade Remessas', 0)))
    
    conn.commit()
    conn.close()
    
# Função para visualizar registros do SQLite
def visualizar_registros_sqlite():
    conn = sqlite3.connect('dados_motoristas.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM motoristas")
    registros = c.fetchall()  # Obtém todos os registros
    
    conn.close()
    
    if registros:
        df = pd.DataFrame(registros, columns=['ID', 'Unidade', 'Motorista', 'Placa', 'Chegada CD', 'Início do Carregamento', 'Fim do Carregamento', 'Quantidade Remessas'])
        # Remove duplicatas mantendo a última ocorrência de cada motorista
        df_unique = df.drop_duplicates(subset='Placa', keep='last')
        st.dataframe(df_unique)
    else:
        st.write("Nenhum registro encontrado no banco de dados.")

# Chama a função para criar a tabela ao iniciar o app
create_database()

st.sidebar.title("Navegação")
page = st.sidebar.radio("Escolha a página", ["Check-in Motoristas", "Visualização de Registros", "Relatório de Registros"])

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
        nome = st.text_input("Nome do Motorista")
        placa = st.text_input("Placa do Veículo", '').upper()  # Converte a placa para maiúsculas

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
                salvar_no_sqlite(dados_motorista)  # Salva no SQLite
                st.success(f"Horário de Chegada registrado: {chegada}")

    # Step 2: Coleta de informações de entrada no CD
    elif subpagina == "Início do Carregamento":
        placa = st.text_input("Placa do Veículo", '').upper()  # Permite que o motorista insira a placa novamente
        if st.button("Check"):
            if not placa:  # Valida se a placa foi inserida
                st.error("Por favor, insira a placa do veículo.")
            else:
                entrada_cd = registrar_horario()
                # Atualiza a entrada no SQLite
                conn = sqlite3.connect('dados_motoristas.db')
                c = conn.cursor()
                c.execute('''UPDATE motoristas SET inicio_carregamento = ? WHERE placa = ?''', 
                          (entrada_cd, placa))
                conn.commit()
                conn.close()
                st.success(f"Horário de Entrada registrado: {entrada_cd}")

    # Step 3: Coleta de informações de saída do CD e quantidade de remessas
    elif subpagina == "Fim do Carregamento":
        placa = st.text_input("Placa do Veículo", '').upper()  # Permite que o motorista insira a placa novamente
        quantidade_remessas = st.number_input("Quantidade de Remessas", min_value=0, value=0)

        if st.button("Check"):
            if not placa:  # Valida se a placa foi inserida
                st.error("Por favor, insira a placa do veículo.")
            else:
                saida_cd = registrar_horario()
                # Atualiza a saída e quantidade de remessas no SQLite
                conn = sqlite3.connect('dados_motoristas.db')
                c = conn.cursor()
                c.execute('''UPDATE motoristas SET fim_carregamento = ?, quantidade_remessas = ? WHERE placa = ?''', 
                          (saida_cd, quantidade_remessas, placa))
                conn.commit()
                conn.close()
                st.success(f"Horário de Saída registrado: {saida_cd}")
                st.success("Check-in registrado com sucesso!")

def salvar_no_sheets(dados):
    dados_lista = list(dados.values())
    worksheet.append_row(dados_lista)

def visualizar_registros_sqlite():
    conn = sqlite3.connect('dados_motoristas.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM motoristas")
    registros = c.fetchall()  # Obtém todos os registros
    
    conn.close()
    
    if registros:
        df = pd.DataFrame(registros, columns=['ID', 'Unidade', 'Motorista', 'Placa', 'Chegada CD', 'Início do Carregamento', 'Fim do Carregamento', 'Quantidade Remessas'])
        # Remove duplicatas mantendo a última ocorrência de cada motorista
        df_unique = df.drop_duplicates(subset='Placa', keep='last')
        st.dataframe(df_unique)
        return df_unique
    else:
        st.write("Nenhum registro encontrado no banco de dados.")
        return pd.DataFrame()  # Retorna um DataFrame vazio se não houver registros

def registros():
    st.title("Visualização - SQLITE3")
    st.write("Após preencher cada etapa de check-in, os dados são enviados para o Banco de Dados SQLITE3 e armazenados para gerar uma visualização em tempo real.")

    # Exibe os registros do SQLite e obtém o DataFrame
    df_registros = visualizar_registros_sqlite()  # Chama a função para visualizar os registros do SQLite
    
    # Adiciona um botão para enviar dados completos para o Google Sheets
    if st.button("Enviar dados completos para o Google Sheets"):
        enviados = 0
        erros = 0
        
        for index, registro in df_registros.iterrows():
            # Verifica se todos os campos estão preenchidos
            if all(pd.notna(registro[1:])):  # Ignora o primeiro campo (ID)
                # Monta o dicionário de dados
                dados_motorista = {
                    'Unidade': registro['Unidade'],
                    'Nome': registro['Motorista'],
                    'Placa': registro['Placa'],
                    'Chegada CD': registro['Chegada CD'],
                    'Início do Carregamento': registro['Início do Carregamento'],
                    'Fim do Carregamento': registro['Fim do Carregamento'],
                    'Quantidade Remessas': registro['Quantidade Remessas']
                }
                # Envia os dados para o Google Sheets
                try:
                    salvar_no_sheets(dados_motorista)
                    enviados += 1
                except Exception as e:
                    st.error(f"Erro ao enviar dados da placa {registro['Placa']}: {str(e)}")
                    erros += 1
        
        # Mensagens de feedback
        if enviados > 0:
            st.success(f"{enviados} registros enviados para o Google Sheets com sucesso!")
        if erros > 0:
            st.error(f"{erros} registros não foram enviados devido a erros.")

def relatorio_registros():
    st.title("Visualização - Google Sheets")
    st.write("Aqui você pode visualizar os dados que foram preenchidos em todos os passos do check-in que foram enviados pela API do Google Sheets.")

    st.markdown("[Google Sheets](https://docs.google.com/spreadsheets/d/1tbJh_GQol0Ax5uB-AjwI26yW9piCIp0peuKV1N5nMeQ/edit?gid=2053463788#gid=2053463788)")

    st.markdown("[Looker Studio](https://lookerstudio.google.com/reporting/e0ec9f83-6e17-4d18-9b44-7b6848f5002d)")

    # Obtém todos os valores da worksheet (retorna uma lista de listas)
    dados = worksheet.get_all_values()

    # Verifica se a planilha contém dados
    if len(dados) > 1:
        # A primeira linha é usada como o cabeçalho (nomes das colunas)
        df = pd.DataFrame(dados[1:], columns=dados[0])

        # Exibe a tabela com os dados no Streamlit
        st.write("Abaixo estão os registros dos motoristas:")
        st.dataframe(df)

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
        elif page == "Relatório de Registros":
            relatorio_registros()  # Função para relatar registros
    else:
        login()  # Se não autenticado, exibe a tela de login

# Adiciona um botão de logout na parte inferior
if st.session_state['authenticated']:
    if st.button("Sair"):
        logout()