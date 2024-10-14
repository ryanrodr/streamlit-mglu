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
                    filial TEXT,
                    nome TEXT,
                    placa TEXT,
                    chegada TEXT,
                    entrada_cd TEXT,
                    saida_cd TEXT,
                    quantidade_remessas INTEGER
                )''')
    conn.commit()
    conn.close()

def salvar_no_sqlite(data):
    conn = sqlite3.connect('dados_motoristas.db')
    c = conn.cursor()
    
    # Insere os dados no banco de dados
    c.execute('''INSERT INTO motoristas (filial, nome, placa, chegada, entrada_cd, saida_cd, quantidade_remessas) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              (data['Filial'], data['Nome'], 
               data['Placa'], data.get('Chegada', ''), 
               data.get('Entrada CD', ''), data.get('Saída CD', ''), 
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
        df = pd.DataFrame(registros, columns=['ID', 'Filial', 'Nome', 'Placa', 'Chegada', 'Entrada CD', 'Saída CD', 'Quantidade Remessas'])
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
    # Inicializa um dicionário para armazenar dados temporários no session_state
    if 'data_temp' not in st.session_state:
        st.session_state.data_temp = {
            'Filial': '',
            'Nome': '',
            'Placa': '',
            'Chegada': '',
            'Entrada CD': '',
            'Saída CD': '',
            'Quantidade Remessas': ''
        }

    # Inicializa um contador de etapas no session_state
    if 'step' not in st.session_state:
        st.session_state.step = 0  # Primeiro passo é a introdução

    # Função para registrar o horário atual
    def registrar_horario(campo):
        br_tz = pytz.timezone('America/Sao_Paulo')
        st.session_state.data_temp[campo] = datetime.now(br_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Função para salvar os dados no Google Sheets
    def salvar_no_sheets(dados):
        dados_lista = list(dados.values())
        worksheet.append_row(dados_lista)

    # Lista de filiais
    lista_filiais = [
        "HVGI - VILA GUILHERME",
        "HUDI - UBERLÂNDIA",
        "HRAO - RIBEIRÃO PRETO",
        "HPPB - PRESIDENTE PRUDENTE",
        "HPLH - PALHOÇA",
        "OSA LM - OSASCO",
        "HITJ - ITAJAÍ",
        "HBHZ - BETIM",
        "HRIO - RIO DE JANEIRO",
        "HPOA - PORTO ALEGRE ( GRAVATAÍ)",
        "HLDB - LONDRINA",
        "HJAB - JABOATÃO DOS GUARARAPES",
        "HSSA - SALVADOR",
        "HCWB - CURITIBA",
        "HBSB - BRASILIA",
        "HGRU - GUARULHOS",
        "HFOR - FORTALEZA",
        "HFCA - FRANCA",
        "HCPQ - CAMPINAS",
        "HBAU - BAURU",
        "HARU - ARAÇATUBA"
    ]

    # Step 0: Introdução
    if st.session_state.step == 0:
        st.title("Check-in de Motoristas.")
        st.write("Clique no botão abaixo para iniciar o processo de check-in.")
        
        if st.button("Iniciar Check-in"):
            st.session_state.step = 1  # Avança diretamente para o passo 1

    # Step 1: Coleta de informações de chegada
    elif st.session_state.step == 1:
        st.session_state.data_temp['Filial'] = st.selectbox("Filial", lista_filiais, index=0)
        st.session_state.data_temp['Nome'] = st.text_input("Nome do Motorista", st.session_state.data_temp['Nome'])
        st.session_state.data_temp['Placa'] = st.text_input("Placa do Veículo", st.session_state.data_temp['Placa'])

        if st.button("Registrar Horário de Chegada"):
            registrar_horario('Chegada')
            st.success(f"Horário de Chegada registrado: {st.session_state.data_temp['Chegada']}")
            salvar_no_sqlite(st.session_state.data_temp)  # Salva no SQLite
            st.session_state.step += 1  # Avança para o próximo passo automaticamente

    # Step 2: Coleta de informações de entrada no CD
    elif st.session_state.step == 2:
        st.write("Etapa 2: Entrada no CD")

        if st.button("Registrar Horário de Entrada no CD"):
            registrar_horario('Entrada CD')
            st.success(f"Horário de Entrada registrado: {st.session_state.data_temp['Entrada CD']}")
            salvar_no_sqlite(st.session_state.data_temp)  # Salva no SQLite
            st.session_state.step += 1  # Avança para o próximo passo automaticamente

    # Step 3: Coleta de informações de saída do CD e quantidade de remessas
    elif st.session_state.step == 3:
        st.write("Etapa 3: Saída do CD e Quantidade de Remessas")

        st.session_state.data_temp['Quantidade Remessas'] = st.number_input(
            "Quantidade de Remessas", min_value=0, value=int(st.session_state.data_temp['Quantidade Remessas'] or 0)
        )

        if st.button("Registrar Horário de Saída do CD"):
            registrar_horario('Saída CD')
            st.success(f"Horário de Saída registrado: {st.session_state.data_temp['Saída CD']}")
            salvar_no_sqlite(st.session_state.data_temp)  # Salva no SQLite
            salvar_no_sheets(st.session_state.data_temp)  # Envia os dados para o Google Sheets
            st.success("Check-in registrado com sucesso!")
            st.session_state.step = 0  # Reinicia o processo

def registros():
    st.title("Visualização - SQLITE3")
    st.write("Após preencher cada etapa de check-in, os dados são enviados para o Banco de Dados SQLITE3 e armazenados para gerar uma visualização em tempo real.")
    
    visualizar_registros_sqlite()  # Chama a função para visualizar os registros do SQLite

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

# Roteamento de páginas
if page == "Check-in Motoristas":
    motoristas()
elif page == "Visualização de Registros":
    registros()
elif page == "Relatório de Registros":
    relatorio_registros()
