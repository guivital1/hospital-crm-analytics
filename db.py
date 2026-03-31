"""
db.py – Banco de dados e utilitários compartilhados
Hospital São Rafael | Challenge FIAP – Sprint 3

Importado tanto por hospital.py quanto por paciente.py
"""

import sqlite3
from datetime import datetime
from exceptions import PacienteDuplicadoError, LeadDuplicadoError
DB_FILE = "hospital.db"


# ══════════════════════════════════════════════════════════════════
#  CONEXÃO
# ══════════════════════════════════════════════════════════════════

def conectar():
    return sqlite3.connect(DB_FILE)


# ══════════════════════════════════════════════════════════════════
#  CRIAÇÃO DAS TABELAS
# ══════════════════════════════════════════════════════════════════

def criar_tabelas():
    with conectar() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS procedimentos (
                id_procedimento        INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria              TEXT NOT NULL,
                nome_especifico        TEXT NOT NULL,
                tipo_especialista      TEXT,
                descricao_complexidade TEXT,
                valor_base             REAL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicos (
                id_medico        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_medico      TEXT NOT NULL,
                crm              TEXT NOT NULL UNIQUE,
                especialidade    TEXT,
                email            TEXT,
                telefone         TEXT,
                cpf              TEXT NOT NULL UNIQUE,
                data_nascimento  TEXT,
                local_hospital   TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS colaboradores (
                id_colaborador  INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT NOT NULL,
                cpf             TEXT NOT NULL UNIQUE,
                data_nascimento TEXT,
                funcao          TEXT,
                status_login    INTEGER DEFAULT 0,
                ultimo_login    TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id_paciente     INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo   TEXT NOT NULL,
                cpf             TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                senha           TEXT NOT NULL,
                telefone        TEXT,
                sexo            TEXT CHECK (sexo IN ('M','F','O')),
                data_nascimento TEXT NOT NULL,
                peso            REAL,
                altura          REAL,
                id_tasy_externo TEXT,
                entrada         TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id_lead           INTEGER PRIMARY KEY AUTOINCREMENT,
                nome              TEXT NOT NULL,
                email             TEXT,
                canal_origem      TEXT,
                telefone          TEXT,
                id_procedimento   INTEGER REFERENCES procedimentos(id_procedimento),
                id_medico_pref    INTEGER REFERENCES medicos(id_medico),
                id_operador       INTEGER REFERENCES colaboradores(id_colaborador),
                status_lead       TEXT DEFAULT 'novo'
                                      CHECK (status_lead IN
                                        ('novo','em atendimento','perdido','convertido','reagendado')),
                data_entrada      TEXT NOT NULL,
                tempo_atendimento TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS grade_agenda (
                id_grade          INTEGER PRIMARY KEY AUTOINCREMENT,
                id_medico         INTEGER NOT NULL REFERENCES medicos(id_medico),
                data_referencia   TEXT NOT NULL,
                hora_inicio       TEXT NOT NULL,
                hora_fim          TEXT NOT NULL,
                tempo_consulta    INTEGER NOT NULL,
                tipo_agenda       TEXT DEFAULT 'Regular'
                                      CHECK (tipo_agenda IN ('Regular','Extra','Bloqueio')),
                motivo_bloqueio   TEXT,
                vagas_disponiveis INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agendamentos (
                id_agendamento  INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente     INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                id_medico       INTEGER NOT NULL REFERENCES medicos(id_medico),
                id_procedimento INTEGER NOT NULL REFERENCES procedimentos(id_procedimento),
                data_hora       TEXT NOT NULL,
                status          TEXT DEFAULT 'agendado'
                                    CHECK (status IN
                                      ('agendado','atendido','falta','cancelado','reagendado','abandono')),
                origem          TEXT DEFAULT 'CRM'
                                    CHECK (origem IN ('CRM','Tasy'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS orcamentos (
                id_orcamento    INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente     INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                id_medico       INTEGER NOT NULL REFERENCES medicos(id_medico),
                id_procedimento INTEGER NOT NULL REFERENCES procedimentos(id_procedimento),
                valor_total     REAL NOT NULL,
                status_orc      TEXT DEFAULT 'aberto'
                                    CHECK (status_orc IN
                                      ('aberto','em andamento','fechado','encerrado')),
                motivo_perda    TEXT,
                data_criacao    TEXT DEFAULT (date('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico_eventos (
                id_evento   INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                area_origem TEXT NOT NULL,
                descricao   TEXT,
                data_evento TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sac (
                id_sac         INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente    INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                motivo         TEXT NOT NULL,
                prazo_limite   TEXT,
                status_solucao TEXT DEFAULT 'pendente'
                                   CHECK (status_solucao IN
                                     ('pendente','em tratativa','resolvido')),
                anexo_url      TEXT,
                data_abertura  TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS mensagens (
                id_msg       INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente  INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                tipo_canal   TEXT NOT NULL
                                 CHECK (tipo_canal IN ('WhatsApp','SMS','E-mail')),
                tipo_gatilho TEXT,
                data_envio   TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pre_cirurgico (
                id_pre           INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente      INTEGER NOT NULL REFERENCES pacientes(id_paciente),
                status_imc       INTEGER DEFAULT 0,
                exames_completos INTEGER DEFAULT 0,
                checklist_ok     INTEGER DEFAULT 0,
                autorizacao_med  INTEGER DEFAULT 0
            )
        """)


# ══════════════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════

def parse_data(s: str):
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s), fmt)
        except ValueError:
            pass
    return None


def total(tabela: str) -> int:
    try:
        with conectar() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    except Exception:
        return 0


def imc_str(peso, altura) -> str:
    if peso and altura:
        return f"{peso / altura**2:.2f}"
    return "-"


def calcular_idade(data_nasc_str: str) -> str:
    dt = parse_data(data_nasc_str)
    if not dt:
        return "-"
    anos = (datetime.now() - dt).days // 365
    return str(anos)


# ── Consultas reutilizáveis ──────────────────────────────────────

def buscar_paciente_cpf(cpf: str):
    with conectar() as conn:
        return conn.execute(
            "SELECT id_paciente, nome_completo, cpf, email, telefone, sexo, "
            "data_nascimento, peso, altura, entrada FROM pacientes WHERE cpf=?", (cpf,)
        ).fetchone()


def buscar_paciente_email(email: str):
    with conectar() as conn:
        return conn.execute(
            "SELECT id_paciente, nome_completo, cpf, email, telefone, sexo, "
            "data_nascimento, peso, altura, entrada FROM pacientes WHERE email=?", (email,)
        ).fetchone()


def listar_medicos_resumo():
    with conectar() as conn:
        return conn.execute(
            "SELECT id_medico, nome_medico, especialidade FROM medicos ORDER BY id_medico"
        ).fetchall()


def listar_procedimentos_resumo():
    with conectar() as conn:
        return conn.execute(
            "SELECT id_procedimento, nome_especifico, valor_base "
            "FROM procedimentos ORDER BY id_procedimento"
        ).fetchall()


def imprimir_paciente(row):
    pid, nome, cpf, email, tel, sexo, nasc, peso, altura, entrada = row
    print(f"\n  ┌─ Paciente #{pid}")
    print(f"  │  Nome       : {nome}")
    print(f"  │  CPF        : {cpf}")
    print(f"  │  E-mail     : {email}")
    print(f"  │  Telefone   : {tel or '-'}")
    print(f"  │  Sexo       : {sexo or '-'}  |  Idade: {calcular_idade(nasc)} anos")
    print(f"  │  Nascimento : {nasc}")
    print(f"  │  Peso       : {peso or '-'} kg  |  Altura: {altura or '-'} m  |  IMC: {imc_str(peso, altura)}")
    print(f"  └─ Entrada    : {entrada}")


def inserir_paciente(dados):
    with conectar() as conn:
        try:
            conn.execute(
                "INSERT INTO pacientes (nome_completo, cpf, email, senha, telefone, sexo, "
                "data_nascimento, peso, altura, entrada) VALUES (?,?,?,?,?,?,?,?,?,?)",
                dados
            )
        except sqlite3.IntegrityError:
            raise PacienteDuplicadoError() ## inserir excessão manualmente para evitar printar o erro do sqlite, e sim a mensagem personalizada da excessão
        
def inserir_paciente(dados):
    with conectar() as conn:
        try:
            conn.execute(
                "INSERT INTO pacientes (nome_completo, cpf, email, senha, telefone, sexo, "
                "data_nascimento, peso, altura, entrada) VALUES (?,?,?,?,?,?,?,?,?,?)",
                dados
            )
        except sqlite3.IntegrityError:
            raise PacienteDuplicadoError()