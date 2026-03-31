"""

Perfil: Colaboradores / Administração
Funcionalidades:
  • Gestão de médicos, procedimentos e colaboradores
  • CRM de leads (visualizar, atribuir, converter)
  • Cadastro e busca de pacientes
  • Agendamentos e grade de agenda
  • Orçamentos, SAC e checklist pré-cirúrgico
  • [DP] Dynamic Programming – recursão, memoização, otimização de agenda
  • [DS] Data Science – análise exploratória e KPIs

Execute:
    python3 hospital.py

Dependências:
    pip install pandas numpy matplotlib seaborn
"""

import sqlite3
import warnings
import time
from datetime import datetime, timedelta
from functools import lru_cache
from db import inserir_paciente
from exceptions import PacienteDuplicadoError

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

from db import (
    criar_tabelas, conectar, parse_data, total, imc_str,
    buscar_paciente_cpf, listar_medicos_resumo,
    listar_procedimentos_resumo, imprimir_paciente
)

warnings.filterwarnings("ignore")
sns.set_theme(style="darkgrid", palette="muted")


# ══════════════════════════════════════════════════════════════════
#  HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════

def _sep(titulo=""):
    print(f"\n{'─'*55}")
    if titulo:
        print(f"  {titulo}")
        print(f"{'─'*55}")


def _show_medicos():
    rows = listar_medicos_resumo()
    if rows:
        print("\n  Médicos disponíveis:")
        for mid, nome, espec in rows:
            print(f"    [{mid}] {nome}  –  {espec or '-'}")
    return rows


def _show_procs():
    rows = listar_procedimentos_resumo()
    if rows:
        print("\n  Procedimentos disponíveis:")
        for pid, nome, valor in rows:
            v = f"R$ {valor:.2f}" if valor else "-"
            print(f"    [{pid}] {nome}  –  {v}")
    return rows


def _show_colabs():
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_colaborador, nome, funcao, status_login FROM colaboradores ORDER BY id_colaborador"
        ).fetchall()
    if rows:
        print("\n  Colaboradores:")
        for cid, nome, func, log in rows:
            st = "🟢" if log else "⚫"
            print(f"    [{cid}] {st} {nome}  –  {func or '-'}")
    return rows


# ══════════════════════════════════════════════════════════════════
#  GESTÃO DE MÉDICOS
# ══════════════════════════════════════════════════════════════════

def cadastrar_medico():
    _sep("Cadastro de Médico")
    nome   = input("  Nome: ").strip()
    crm    = input("  CRM (ex: CRM-SP 123456): ").strip()
    espec  = input("  Especialidade: ").strip()
    email  = input("  E-mail: ").strip()
    tel    = input("  Telefone: ").strip()
    cpf    = input("  CPF (somente números): ").strip()
    nasc   = input("  Data de nascimento (DD/MM/AAAA): ").strip()
    local  = input("  Local/hospital (opcional): ").strip()

    if not nome or not crm or not cpf:
        print("  ✗ Nome, CRM e CPF são obrigatórios.")
        return
    try:
        with conectar() as conn:
            conn.execute(
                "INSERT INTO medicos (nome_medico, crm, especialidade, email, telefone, "
                "cpf, data_nascimento, local_hospital) VALUES (?,?,?,?,?,?,?,?)",
                (nome, crm, espec or None, email or None, tel or None,
                 cpf, nasc or None, local or None)
            )
        print("  ✓ Médico cadastrado.")
    except sqlite3.IntegrityError:
        print("  ✗ CRM ou CPF já cadastrado.")


def listar_medicos():
    _sep("Médicos Cadastrados")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_medico, nome_medico, crm, especialidade, email, telefone, local_hospital "
            "FROM medicos ORDER BY id_medico"
        ).fetchall()
    if not rows:
        print("  Nenhum médico cadastrado.")
        return
    for mid, nome, crm, espec, email, tel, local in rows:
        print(f"\n  [{mid}] {nome}  |  CRM: {crm}")
        print(f"       Especialidade: {espec or '-'}  |  Tel: {tel or '-'}")
        print(f"       E-mail: {email or '-'}  |  Local: {local or '-'}")


def remover_medico():
    _sep("Remover Médico")
    _show_medicos()
    mid = input("\n  ID do médico para remover: ").strip()
    if not mid.isdigit():
        print("  ✗ ID inválido.")
        return
    with conectar() as conn:
        n = conn.execute("DELETE FROM medicos WHERE id_medico=?", (int(mid),)).rowcount
    print("  ✓ Médico removido." if n else "  ✗ Médico não encontrado.")


# ══════════════════════════════════════════════════════════════════
#  GESTÃO DE PROCEDIMENTOS
# ══════════════════════════════════════════════════════════════════

def cadastrar_procedimento():
    _sep("Cadastro de Procedimento")
    cat    = input("  Categoria (ex: Plástica, Dermatologia): ").strip()
    nome   = input("  Nome específico (ex: Rinoplastia): ").strip()
    espec  = input("  Tipo de especialista: ").strip()
    desc   = input("  Descrição/complexidade: ").strip()
    valor  = input("  Valor base (R$): ").strip()

    if not cat or not nome:
        print("  ✗ Categoria e nome são obrigatórios.")
        return
    try:
        v = float(valor) if valor else None
    except ValueError:
        print("  ✗ Valor inválido.")
        return

    with conectar() as conn:
        conn.execute(
            "INSERT INTO procedimentos (categoria, nome_especifico, tipo_especialista, "
            "descricao_complexidade, valor_base) VALUES (?,?,?,?,?)",
            (cat, nome, espec or None, desc or None, v)
        )
    print("  ✓ Procedimento cadastrado.")


def listar_procedimentos():
    _sep("Procedimentos Cadastrados")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_procedimento, categoria, nome_especifico, tipo_especialista, valor_base "
            "FROM procedimentos ORDER BY categoria, id_procedimento"
        ).fetchall()
    if not rows:
        print("  Nenhum procedimento cadastrado.")
        return
    cat_atual = ""
    for pid, cat, nome, espec, valor in rows:
        if cat != cat_atual:
            print(f"\n  ── {cat} ──")
            cat_atual = cat
        v = f"R$ {valor:.2f}" if valor else "-"
        print(f"    [{pid}] {nome}  |  {espec or '-'}  |  {v}")


def remover_procedimento():
    _sep("Remover Procedimento")
    _show_procs()
    pid = input("\n  ID do procedimento para remover: ").strip()
    if not pid.isdigit():
        print("  ✗ ID inválido.")
        return
    with conectar() as conn:
        n = conn.execute("DELETE FROM procedimentos WHERE id_procedimento=?", (int(pid),)).rowcount
    print("  ✓ Procedimento removido." if n else "  ✗ Procedimento não encontrado.")


# ══════════════════════════════════════════════════════════════════
#  GESTÃO DE COLABORADORES
# ══════════════════════════════════════════════════════════════════

def cadastrar_colaborador():
    _sep("Cadastro de Colaborador")
    nome  = input("  Nome: ").strip()
    cpf   = input("  CPF (somente números): ").strip()
    nasc  = input("  Data de nascimento (DD/MM/AAAA): ").strip()
    func  = input("  Função (Vendas / Recepção / SAC): ").strip()

    if not nome or not cpf:
        print("  ✗ Nome e CPF são obrigatórios.")
        return
    try:
        with conectar() as conn:
            conn.execute(
                "INSERT INTO colaboradores (nome, cpf, data_nascimento, funcao, status_login, ultimo_login) "
                "VALUES (?,?,?,?,0,?)",
                (nome, cpf, nasc or None, func or None,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        print("  ✓ Colaborador cadastrado.")
    except sqlite3.IntegrityError:
        print("  ✗ CPF já cadastrado.")


def listar_colaboradores():
    _sep("Colaboradores")
    _show_colabs()


def admin_toggle_login_colaborador():
    _sep("Alterar Status de Login")
    _show_colabs()
    cid = input("\n  ID do colaborador: ").strip()
    if not cid.isdigit():
        print("  ✗ ID inválido.")
        return
    with conectar() as conn:
        row = conn.execute(
            "SELECT status_login FROM colaboradores WHERE id_colaborador=?", (int(cid),)
        ).fetchone()
        if not row:
            print("  ✗ Colaborador não encontrado.")
            return
        novo = 0 if row[0] else 1
        conn.execute(
            "UPDATE colaboradores SET status_login=?, ultimo_login=? WHERE id_colaborador=?",
            (novo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(cid))
        )
    print(f"  ✓ Status alterado para {'🟢 Logado' if novo else '⚫ Deslogado'}.") ## FUNÇÃO MANUALLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL em pleno 206 eu to maluco

def login_colaborador():
    _sep("Login do Colaborador")

    cpf = input("  CPF: ").strip()

    with conectar() as conn:
        colab = conn.execute(
            "SELECT id_colaborador, nome, status_login FROM colaboradores WHERE cpf=?",
            (cpf,)
        ).fetchone()

        if not colab:
            print("  ✗ Colaborador não encontrado.")
            return None

        id_colab, nome, status = colab

        if status == 1:
            print("  ⚠ Já está logado.")
            return id_colab

        conn.execute(
            "UPDATE colaboradores SET status_login=1, ultimo_login=? WHERE id_colaborador=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_colab)
        )

    print(f"  ✓ {nome} logado com sucesso.")
    return id_colab ## viva a automatização em 2026 

def logout_colaborador(id_colab):
    with conectar() as conn:
        conn.execute(
            "UPDATE colaboradores SET status_login=0 WHERE id_colaborador=?",
            (id_colab,)
        )
    print("  ✓ Logout realizado.")
# ══════════════════════════════════════════════════════════════════
#  CRM – PACIENTES
# ══════════════════════════════════════════════════════════════════

def cadastrar_paciente():
    _sep("Cadastro de Paciente (pelo hospital)")
    nome   = input("  Nome completo: ").strip()
    cpf    = input("  CPF (somente números): ").strip()
    email  = input("  E-mail: ").strip()
    senha  = input("  Senha de acesso: ").strip()
    tel    = input("  Telefone (WhatsApp): ").strip()
    sexo   = input("  Sexo (M/F/O): ").strip().upper()
    nasc   = input("  Data de nascimento (DD/MM/AAAA): ").strip()
    peso_t = input("  Peso em kg (ex: 72.0): ").strip()
    alt_t  = input("  Altura em m (ex: 1.80): ").strip()

    if not nome or not cpf or not email or not senha or not nasc:
        print("  Campos obrigatórios faltando.")
        return

    try:
        peso   = float(peso_t) if peso_t else None
        altura = float(alt_t)  if alt_t  else None
    except ValueError:
        print("  Peso ou altura inválidos.")
        return

    if peso and altura:
        print(f"  IMC: {peso/altura**2:.2f}")

    entrada = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        inserir_paciente((
            nome, cpf, email, senha,
            tel or None, sexo or None,
            nasc, peso, altura, entrada
        ))
        print("  Paciente cadastrado.")

    except PacienteDuplicadoError as e:
        print(f"  Erro: {e}")



def buscar_paciente_hospital():
    _sep("Buscar Paciente")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return None
    imprimir_paciente(row)
    return row


def listar_pacientes():
    _sep("Todos os Pacientes")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_paciente, nome_completo, cpf, email, telefone, sexo, "
            "data_nascimento, peso, altura, entrada FROM pacientes ORDER BY id_paciente"
        ).fetchall()
    if not rows:
        print("  Nenhum paciente cadastrado.")
        return
    for row in rows:
        imprimir_paciente(row)


def remover_paciente():
    _sep("Remover Paciente")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid = row[0]
    conf = input(f"  Confirmar remoção de '{row[1]}'? (s/n): ").strip().lower()
    if conf != "s":
        print("  Operação cancelada.")
        return
    with conectar() as conn:
        for t in ("historico_eventos","sac","mensagens","pre_cirurgico","agendamentos","orcamentos"):
            conn.execute(f"DELETE FROM {t} WHERE id_paciente=?", (pid,))
        conn.execute("DELETE FROM pacientes WHERE id_paciente=?", (pid,))
    print("  ✓ Paciente removido.")


# ══════════════════════════════════════════════════════════════════
#  CRM – LEADS
# ══════════════════════════════════════════════════════════════════

def listar_leads():
    _sep("Leads")
    status_f = input("  Filtrar por status (ou Enter para todos): ").strip()
    with conectar() as conn:
        if status_f:
            rows = conn.execute(
                "SELECT l.id_lead, l.nome, l.canal_origem, l.status_lead, l.data_entrada, "
                "l.telefone, p.nome_especifico, m.nome_medico, c.nome "
                "FROM leads l "
                "LEFT JOIN procedimentos p ON l.id_procedimento=p.id_procedimento "
                "LEFT JOIN medicos m ON l.id_medico_pref=m.id_medico "
                "LEFT JOIN colaboradores c ON l.id_operador=c.id_colaborador "
                "WHERE l.status_lead=? ORDER BY l.data_entrada DESC", (status_f,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT l.id_lead, l.nome, l.canal_origem, l.status_lead, l.data_entrada, "
                "l.telefone, p.nome_especifico, m.nome_medico, c.nome "
                "FROM leads l "
                "LEFT JOIN procedimentos p ON l.id_procedimento=p.id_procedimento "
                "LEFT JOIN medicos m ON l.id_medico_pref=m.id_medico "
                "LEFT JOIN colaboradores c ON l.id_operador=c.id_colaborador "
                "ORDER BY l.data_entrada DESC"
            ).fetchall()

    if not rows:
        print("  Nenhum lead encontrado.")
        return

    status_cores = {
        "novo": "🔵", "em atendimento": "🟡",
        "convertido": "🟢", "perdido": "🔴", "reagendado": "🟠"
    }
    for lid, nome, canal, status, entrada, tel, proc, med, oper in rows:
        icone = status_cores.get(status, "⚪")
        print(f"\n  {icone} [{lid}] {nome}  |  {canal or '-'}  |  Tel: {tel or '-'}")
        print(f"       Status: {status}  |  Entrada: {entrada}")
        print(f"       Procedimento: {proc or '-'}  |  Médico pref.: {med or '-'}")
        print(f"       Operador: {oper or 'Não atribuído'}")


def cadastrar_lead():
    _sep("Cadastro de Lead")
    _show_procs()
    _show_medicos()
    _show_colabs()

    nome     = input("\n  Nome: ").strip()
    email    = input("  E-mail: ").strip()
    canal    = input("  Canal (Instagram/Google/Facebook/TikTok/Indicação): ").strip()
    tel      = input("  Telefone: ").strip()
    id_proc  = input("  ID do procedimento de interesse (ou Enter): ").strip()
    id_med   = input("  ID do médico de preferência (ou Enter): ").strip()
    id_oper  = input("  ID do operador responsável (ou Enter): ").strip()

    if not nome:
        print("  ✗ Nome obrigatório.")
        return

    with conectar() as conn:
        conn.execute(
            "INSERT INTO leads (nome, email, canal_origem, telefone, id_procedimento, "
            "id_medico_pref, id_operador, status_lead, data_entrada) VALUES (?,?,?,?,?,?,?,'novo',?)",
            (nome, email or None, canal or None, tel or None,
             int(id_proc) if id_proc.isdigit() else None,
             int(id_med)  if id_med.isdigit()  else None,
             int(id_oper) if id_oper.isdigit() else None,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    print("  ✓ Lead cadastrado.")


def atualizar_status_lead():
    _sep("Atualizar Status do Lead")

    with conectar() as conn:
        leads = conn.execute(
            "SELECT id_lead, nome, status_lead, data_entrada FROM leads ORDER BY id_lead"
        ).fetchall()

    if not leads:
        print("  Nenhum lead cadastrado.")
        return

    print("\n  Leads:")
    for l in leads:
        print(f"  ID {l[0]} | {l[1]} | Status: {l[2]}")

    lid = input("\n  ID do lead: ").strip()
    if not lid.isdigit():
        print("  ✗ ID inválido.")
        return

    print("\n  Status disponíveis:")
    print("  novo | em atendimento | convertido | perdido | reagendado")

    novo = input("  Novo status: ").strip().lower()

    status_validos = ['novo','em atendimento','convertido','perdido','reagendado']

    if novo not in status_validos:
        print("  ✗ Status inválido.")
        return

    with conectar() as conn:
        lead = conn.execute(
            "SELECT data_entrada FROM leads WHERE id_lead=?",
            (int(lid),)
        ).fetchone()

        if not lead:
            print("  ✗ Lead não encontrado.")
            return

        tempo = None

        # calcula tempo de atendimento
        if novo in ['em atendimento', 'convertido']:
            entrada = datetime.strptime(lead[0], "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - entrada
            tempo = str(delta)

        conn.execute(
            "UPDATE leads SET status_lead=?, tempo_atendimento=? WHERE id_lead=?",
            (novo, tempo, int(lid))
        )

    print("  ✓ Status atualizado com sucesso.")
    
    
def relatar_leads_por_canal():
    _sep("Relatório: Leads por Canal")

    with conectar() as conn:
        rows = conn.execute(
            "SELECT canal_origem, COUNT(*) FROM leads GROUP BY canal_origem"
        ).fetchall()

    for canal, total in rows:
        print(f"  {canal or 'Não informado'}: {total}")
        
def relatorio_taxa_conversao():
    _sep("Relatório: Taxa de Conversão")

    with conectar() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        convertidos = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE status_lead='convertido'"
        ).fetchone()[0]

    if total == 0:
        print("  Nenhum lead cadastrado.")
        return

    taxa = (convertidos / total) * 100

    print(f"  Convertidos: {convertidos}/{total}")
    print(f"  Taxa: {taxa:.2f}%")

def relatorio_total_pacientes():
    _sep("Relatório: Total de Pacientes")

    with conectar() as conn:
        total = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]

    print(f"  Total de pacientes cadastrados: {total}")
    
def relatorio_medicos_mais_procurados():
    _sep("Relatório: Médicos mais procurados")

    with conectar() as conn:
        rows = conn.execute("""
            SELECT m.nome_medico, COUNT(l.id_lead) as total
            FROM leads l
            JOIN medicos m ON l.id_medico_pref = m.id_medico
            GROUP BY m.nome_medico
            ORDER BY total DESC
        """).fetchall()

    for nome, total in rows:
        print(f"  {nome}: {total} lead(s)")
        
def menu_relatorios():
    while True:
        _sep("RELATÓRIOS")

        print("1 - Leads por canal")
        print("2 - Taxa de conversão")
        print("3 - Total de pacientes")
        print("4 - Médicos mais procurados")
        print("0 - Voltar")

        op = input("Escolha: ").strip()

        if op == "1":
            relatar_leads_por_canal()
        elif op == "2":
            relatorio_taxa_conversao()
        elif op == "3":
            relatorio_total_pacientes()
        elif op == "4":
            relatorio_medicos_mais_procurados()
        elif op == "0":
            break
        else:
            print("  Opção inválida.")
    
def relatorio_funil_leads():
    _sep("Relatório: Funil de Leads")

    with conectar() as conn:
        rows = conn.execute("""
            SELECT status_lead, COUNT(*)
            FROM leads
            GROUP BY status_lead
        """).fetchall()

    total = sum(r[1] for r in rows)

    for status, qtd in rows:
        perc = (qtd / total) * 100 if total else 0
        print(f"  {status}: {qtd} ({perc:.1f}%)")
    
def relatorio_tempo_medio():
    _sep("Relatório: Tempo Médio de Atendimento")

    with conectar() as conn:
        rows = conn.execute("""
            SELECT tempo_atendimento FROM leads
            WHERE tempo_atendimento IS NOT NULL
        """).fetchall()

    if not rows:
        print("  Nenhum dado disponível.")
        return

    total_seg = 0

    for (t,) in rows:
        h, m, s = t.split(":")
        total_seg += int(h)*3600 + int(m)*60 + int(float(s))

    media = total_seg / len(rows)

    h = int(media // 3600)
    m = int((media % 3600) // 60)

    print(f"  Tempo médio: {h}h {m}min")
    
# ══════════════════════════════════════════════════════════════════
#  CRM – AGENDAMENTOS
# ══════════════════════════════════════════════════════════════════

def cadastrar_agendamento():
    _sep("Novo Agendamento")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid = row[0]
    print(f"  Paciente: {row[1]}")

    _show_medicos()
    _show_procs()

    id_med  = input("\n  ID do médico: ").strip()
    id_proc = input("  ID do procedimento: ").strip()
    dh      = input("  Data e hora (DD/MM/AAAA HH:MM): ").strip()
    origem  = input("  Origem (CRM/Tasy) [CRM]: ").strip() or "CRM"

    if not id_med.isdigit() or not id_proc.isdigit():
        print("  ✗ IDs inválidos.")
        return
    dt = parse_data(dh)
    if not dt:
        print("  ✗ Data/hora inválida.")
        return

    with conectar() as conn:
        conn.execute(
            "INSERT INTO agendamentos (id_paciente, id_medico, id_procedimento, data_hora, status, origem) "
            "VALUES (?,?,?,?,'agendado',?)",
            (pid, int(id_med), int(id_proc), dt.strftime("%Y-%m-%d %H:%M:%S"), origem)
        )
    print("  ✓ Agendamento criado.")


def listar_agendamentos():
    _sep("Agendamentos")
    status_f = input("  Filtrar por status (ou Enter para todos): ").strip()
    with conectar() as conn:
        q = """
            SELECT a.id_agendamento, p.nome_completo, m.nome_medico,
                   pr.nome_especifico, a.data_hora, a.status, a.origem
            FROM agendamentos a
            JOIN pacientes p    ON a.id_paciente=p.id_paciente
            JOIN medicos m      ON a.id_medico=m.id_medico
            JOIN procedimentos pr ON a.id_procedimento=pr.id_procedimento
        """
        rows = conn.execute(
            q + ("WHERE a.status=? ORDER BY a.data_hora" if status_f else "ORDER BY a.data_hora"),
            (status_f,) if status_f else ()
        ).fetchall()
    if not rows:
        print("  Nenhum agendamento encontrado.")
        return
    for aid, pac, med, proc, dt, status, origem in rows:
        print(f"\n  [{aid}] {pac}")
        print(f"       Médico: {med}  |  Procedimento: {proc}")
        print(f"       Data: {dt}  |  Status: {status}  |  Origem: {origem}")


def atualizar_status_agendamento():
    _sep("Atualizar Status de Agendamento")
    aid = input("  ID do agendamento: ").strip()
    if not aid.isdigit():
        print("  ✗ ID inválido.")
        return
    print("  Status: agendado | atendido | falta | cancelado | reagendado | abandono")
    novo = input("  Novo status: ").strip()
    with conectar() as conn:
        n = conn.execute(
            "UPDATE agendamentos SET status=? WHERE id_agendamento=?", (novo, int(aid))
        ).rowcount
    print("  ✓ Status atualizado." if n else "  ✗ Agendamento não encontrado.")


# ══════════════════════════════════════════════════════════════════
#  GRADE DE AGENDA
# ══════════════════════════════════════════════════════════════════

def cadastrar_grade():
    _sep("Grade de Agenda")
    _show_medicos()
    id_med = input("\n  ID do médico: ").strip()
    data   = input("  Data (DD/MM/AAAA): ").strip()
    h_ini  = input("  Hora início (HH:MM): ").strip()
    h_fim  = input("  Hora fim   (HH:MM): ").strip()
    t_con  = input("  Minutos por consulta (ex: 45): ").strip()
    tipo   = input("  Tipo (Regular/Extra/Bloqueio) [Regular]: ").strip().capitalize() or "Regular"
    motivo = ""
    if tipo == "Bloqueio":
        motivo = input("  Motivo do bloqueio (obrigatório): ").strip()
        if not motivo:
            print("  ✗ Motivo obrigatório para bloqueio.")
            return

    if not id_med.isdigit() or not t_con.isdigit():
        print("  ✗ Dados inválidos.")
        return
    dt = parse_data(data)
    if not dt:
        print("  ✗ Data inválida.")
        return

    try:
        h, m = map(int, h_ini.split(":")), map(int, h_fim.split(":"))
        ini_min = list(h)[0]*60 + list(map(int, h_ini.split(":")))[1]
        fim_min = list(map(int, h_fim.split(":")))[0]*60 + list(map(int, h_fim.split(":")))[1]
        vagas   = 0 if tipo == "Bloqueio" else (fim_min - ini_min) // int(t_con)
    except Exception:
        vagas = 0

    with conectar() as conn:
        conn.execute(
            "INSERT INTO grade_agenda (id_medico, data_referencia, hora_inicio, hora_fim, "
            "tempo_consulta, tipo_agenda, motivo_bloqueio, vagas_disponiveis) VALUES (?,?,?,?,?,?,?,?)",
            (int(id_med), dt.strftime("%Y-%m-%d"), h_ini, h_fim,
             int(t_con), tipo, motivo or None, vagas)
        )
    print(f"  ✓ Grade cadastrada.{' Vagas: '+str(vagas) if tipo!='Bloqueio' else ''}")


def listar_grade():
    _sep("Grade de Agenda")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT g.id_grade, m.nome_medico, g.data_referencia, g.hora_inicio, "
            "g.hora_fim, g.tempo_consulta, g.tipo_agenda, g.vagas_disponiveis, g.motivo_bloqueio "
            "FROM grade_agenda g JOIN medicos m ON g.id_medico=m.id_medico "
            "ORDER BY g.data_referencia, g.hora_inicio"
        ).fetchall()
    if not rows:
        print("  Nenhuma grade cadastrada.")
        return
    for gid, med, data, h_ini, h_fim, t_con, tipo, vagas, motivo in rows:
        print(f"\n  [{gid}] {med}  –  {data}  |  {h_ini}–{h_fim}")
        print(f"       Tipo: {tipo}  |  {t_con} min/consulta  |  Vagas: {vagas}")
        if motivo:
            print(f"       Motivo: {motivo}")


# ══════════════════════════════════════════════════════════════════
#  ORÇAMENTOS
# ══════════════════════════════════════════════════════════════════

def cadastrar_orcamento():
    _sep("Novo Orçamento")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid = row[0]
    print(f"  Paciente: {row[1]}")

    _show_medicos()
    _show_procs()

    id_med  = input("\n  ID do médico: ").strip()
    id_proc = input("  ID do procedimento: ").strip()
    valor   = input("  Valor total (R$): ").strip()

    if not id_med.isdigit() or not id_proc.isdigit():
        print("  ✗ IDs inválidos.")
        return
    try:
        v = float(valor)
    except ValueError:
        print("  ✗ Valor inválido.")
        return

    with conectar() as conn:
        conn.execute(
            "INSERT INTO orcamentos (id_paciente, id_medico, id_procedimento, valor_total, status_orc) "
            "VALUES (?,?,?,?,'aberto')",
            (pid, int(id_med), int(id_proc), v)
        )
    print("  ✓ Orçamento criado.")


def listar_orcamentos():
    _sep("Orçamentos")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT o.id_orcamento, p.nome_completo, m.nome_medico, pr.nome_especifico, "
            "o.valor_total, o.status_orc, o.data_criacao, o.motivo_perda "
            "FROM orcamentos o "
            "JOIN pacientes p ON o.id_paciente=p.id_paciente "
            "JOIN medicos m ON o.id_medico=m.id_medico "
            "JOIN procedimentos pr ON o.id_procedimento=pr.id_procedimento "
            "ORDER BY o.data_criacao DESC"
        ).fetchall()
    if not rows:
        print("  Nenhum orçamento.")
        return
    for oid, pac, med, proc, valor, status, data, motivo in rows:
        print(f"\n  [{oid}] {pac}  |  R$ {valor:.2f}  |  {status}")
        print(f"       Médico: {med}  |  Procedimento: {proc}  |  Data: {data}")
        if motivo:
            print(f"       Motivo perda: {motivo}")


def atualizar_status_orcamento():
    _sep("Atualizar Status de Orçamento")
    oid = input("  ID do orçamento: ").strip()
    if not oid.isdigit():
        print("  ✗ ID inválido.")
        return
    print("  Status: aberto | em andamento | fechado | encerrado")
    novo = input("  Novo status: ").strip()
    motivo = ""
    if novo == "encerrado":
        motivo = input("  Motivo da perda (obrigatório): ").strip()
        if not motivo:
            print("  ✗ Motivo obrigatório para encerramento.")
            return
    with conectar() as conn:
        n = conn.execute(
            "UPDATE orcamentos SET status_orc=?, motivo_perda=? WHERE id_orcamento=?",
            (novo, motivo or None, int(oid))
        ).rowcount
    print("  ✓ Status atualizado." if n else "  ✗ Orçamento não encontrado.")


# ══════════════════════════════════════════════════════════════════
#  SAC
# ══════════════════════════════════════════════════════════════════

def cadastrar_sac():
    _sep("Abertura de SAC")
    cpf    = input("  CPF do paciente: ").strip()
    row    = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid    = row[0]
    motivo = input("  Motivo da reclamação: ").strip()
    if not motivo:
        print("  ✗ Motivo obrigatório.")
        return
    prazo = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        conn.execute(
            "INSERT INTO sac (id_paciente, motivo, prazo_limite, status_solucao) VALUES (?,?,?,'pendente')",
            (pid, motivo, prazo)
        )
    print(f"  ✓ SAC aberto. Prazo: {prazo}")


def listar_sac():
    _sep("SAC – Reclamações")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT s.id_sac, p.nome_completo, s.motivo, s.status_solucao, "
            "s.prazo_limite, s.data_abertura "
            "FROM sac s JOIN pacientes p ON s.id_paciente=p.id_paciente "
            "ORDER BY s.data_abertura DESC"
        ).fetchall()
    if not rows:
        print("  Nenhum SAC aberto.")
        return
    for sid, pac, motivo, status, prazo, abertura in rows:
        vencido = ""
        if prazo and parse_data(prazo) and parse_data(prazo) < datetime.now() and status != "resolvido":
            vencido = "  ⚠ PRAZO VENCIDO"
        print(f"\n  [{sid}] {pac}  |  {status}{vencido}")
        print(f"       Motivo: {motivo}")
        print(f"       Prazo: {prazo}  |  Abertura: {abertura}")


def atualizar_sac():
    _sep("Atualizar SAC")
    sid = input("  ID do SAC: ").strip()
    if not sid.isdigit():
        print("  ✗ ID inválido.")
        return
    print("  Status: pendente | em tratativa | resolvido")
    novo = input("  Novo status: ").strip()
    with conectar() as conn:
        n = conn.execute(
            "UPDATE sac SET status_solucao=? WHERE id_sac=?", (novo, int(sid))
        ).rowcount
    print("  ✓ SAC atualizado." if n else "  ✗ SAC não encontrado.")


# ══════════════════════════════════════════════════════════════════
#  CHECKLIST PRÉ-CIRÚRGICO
# ══════════════════════════════════════════════════════════════════

def cadastrar_pre_cirurgico():
    _sep("Checklist Pré-Cirúrgico")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid = row[0]
    print(f"  Paciente: {row[1]}  |  IMC: {imc_str(row[7], row[8])}")

    def flag(p): return 1 if input(f"  {p} (s/n): ").strip().lower() == "s" else 0

    imc  = flag("IMC dentro do limite aprovado?")
    exam = flag("Exames completos?")
    chk  = flag("Checklist de segurança aprovado?")
    aut  = flag("Autorização médica assinada?")

    with conectar() as conn:
        conn.execute(
            "INSERT INTO pre_cirurgico (id_paciente, status_imc, exames_completos, "
            "checklist_ok, autorizacao_med) VALUES (?,?,?,?,?)",
            (pid, imc, exam, chk, aut)
        )
    aprovado = all([imc, exam, chk, aut])
    print(f"  ✓ Checklist salvo.  {'✅ Paciente APTO.' if aprovado else '⚠ Paciente PENDENTE.'}")


def listar_pre_cirurgico():
    _sep("Checklist Pré-Cirúrgico – Todos")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT p.nome_completo, p.cpf, pc.status_imc, pc.exames_completos, "
            "pc.checklist_ok, pc.autorizacao_med "
            "FROM pre_cirurgico pc JOIN pacientes p ON pc.id_paciente=p.id_paciente "
            "ORDER BY p.nome_completo"
        ).fetchall()
    if not rows:
        print("  Nenhum checklist registrado.")
        return
    for nome, cpf, imc, exam, chk, aut in rows:
        ok = lambda v: "✅" if v else "❌"
        apto = "✅ APTO" if all([imc, exam, chk, aut]) else "⚠ PENDENTE"
        print(f"\n  {nome}  |  CPF: {cpf}  |  {apto}")
        print(f"  IMC: {ok(imc)}  Exames: {ok(exam)}  Checklist: {ok(chk)}  Autorização: {ok(aut)}")


# ══════════════════════════════════════════════════════════════════
#  HISTÓRICO DO PACIENTE
# ══════════════════════════════════════════════════════════════════

def historico_paciente():
    _sep("Histórico Completo do Paciente")
    cpf = input("  CPF do paciente: ").strip()
    row = buscar_paciente_cpf(cpf)
    if not row:
        print("  ✗ Paciente não encontrado.")
        return
    pid = row[0]
    imprimir_paciente(row)

    with conectar() as conn:
        agds = conn.execute(
            "SELECT a.data_hora, pr.nome_especifico, m.nome_medico, a.status "
            "FROM agendamentos a "
            "JOIN procedimentos pr ON a.id_procedimento=pr.id_procedimento "
            "JOIN medicos m ON a.id_medico=m.id_medico "
            "WHERE a.id_paciente=? ORDER BY a.data_hora", (pid,)
        ).fetchall()

        orcs = conn.execute(
            "SELECT o.data_criacao, pr.nome_especifico, o.valor_total, o.status_orc "
            "FROM orcamentos o JOIN procedimentos pr ON o.id_procedimento=pr.id_procedimento "
            "WHERE o.id_paciente=? ORDER BY o.data_criacao", (pid,)
        ).fetchall()

        msgs = conn.execute(
            "SELECT data_envio, tipo_canal, tipo_gatilho FROM mensagens "
            "WHERE id_paciente=? ORDER BY data_envio", (pid,)
        ).fetchall()

    print(f"\n  ── Agendamentos ({len(agds)}) ──")
    for dt, proc, med, status in agds:
        print(f"    {dt}  |  {proc}  |  {med}  |  {status}")

    print(f"\n  ── Orçamentos ({len(orcs)}) ──")
    for dt, proc, valor, status in orcs:
        print(f"    {dt}  |  {proc}  |  R$ {valor:.2f}  |  {status}")

    print(f"\n  ── Mensagens Enviadas ({len(msgs)}) ──")
    for dt, canal, gatilho in msgs:
        print(f"    {dt}  |  {canal}  |  {gatilho or '-'}")


# ══════════════════════════════════════════════════════════════════
#  [A] DYNAMIC PROGRAMMING
# ══════════════════════════════════════════════════════════════════

def verificar_duplicidade_recursivo(novo: dict, cadastros: list, i: int = 0) -> bool:
    """Percorre recursivamente verificando CPF e nome. Complexidade O(n)."""
    if i >= len(cadastros):
        return False
    atual = cadastros[i]
    if (atual["cpf"].strip() == novo["cpf"].strip() or
            atual["nome"].strip().lower() == novo["nome"].strip().lower()):
        print(f"    ↳ Duplicata no índice {i}: CPF={atual['cpf']} | Nome={atual['nome']}")
        return True
    return verificar_duplicidade_recursivo(novo, cadastros, i + 1)


_cache: dict = {}


def comparar_com_cache(cpf_a: str, cpf_b: str) -> bool:
    """Memoização manual — evita recalcular pares já comparados."""
    chave = tuple(sorted([cpf_a.strip(), cpf_b.strip()]))
    if chave in _cache:
        print(f"    ↳ [CACHE HIT]  {chave}")
        return _cache[chave]
    _cache[chave] = chave[0] == chave[1]
    print(f"    ↳ [CACHE MISS] {chave} → armazenado")
    return _cache[chave]


def verificar_com_memoizacao(novo: dict, base: list) -> bool:
    for c in base:
        if comparar_com_cache(novo["cpf"], c["cpf"]):
            return True
    return False


@lru_cache(maxsize=512)
def comparar_cpf_lru(a: str, b: str) -> bool:
    return a.strip() == b.strip()


def calcular_melhor_agenda(dur: int, slots: list, i: int = 0,
                           atual: list = None, melhor: list = None) -> list:
    """Backtracking recursivo — maximiza consultas sem sobreposição."""
    if atual  is None: atual  = []
    if melhor is None: melhor = []
    if len(atual) > len(melhor): melhor = list(atual)
    if i >= len(slots): return melhor

    ini, fim = slots[i]
    cap = fim - ini
    if cap >= dur:
        n     = cap // dur
        novos = [(ini + j*dur, ini + (j+1)*dur) for j in range(n)]
        melhor = calcular_melhor_agenda(dur, slots, i+1, atual+novos, melhor)
    melhor = calcular_melhor_agenda(dur, slots, i+1, atual, melhor)
    return melhor


def minutos_para_hora(m: int) -> str:
    return f"{m//60:02d}:{m%60:02d}"


def menu_dp():
    with conectar() as conn:
        rows = conn.execute("SELECT nome_completo, cpf FROM pacientes").fetchall()
    cadastros = [{"nome": r[0], "cpf": r[1]} for r in rows]
    n = len(cadastros) ## busca pacientes no banco // transforma em lista de dicionario

    print(f"\n{'═'*55}")
    print(f"  [DP] DYNAMIC PROGRAMMING  ({n} paciente(s) no banco)")
    print(f"{'═'*55}")

    base = cadastros if cadastros else [
        {"nome": "Carlos Lima",   "cpf": "22222222222"},
        {"nome": "Beatriz Nunes", "cpf": "33333333333"},
    ]
    lead_dup = {"nome": base[0]["nome"], "cpf": base[0]["cpf"]}
    
    ## nao tem dados reais? usa exemplos para demonstrar as tarefas (apenas exemplo para a disciplina de programacao dinamica)

    # Tarefa 1
    _sep("TAREFA 1 – Verificação Recursiva de Duplicidade")
    for lead in [{"nome": "Lead Completamente Novo", "cpf": "00000000000"}, lead_dup]:
        print(f"\n  Verificando: {lead['nome']}  |  CPF: {lead['cpf']}")
        r = verificar_duplicidade_recursivo(lead, base)
        print(f"  → {'DUPLICATA – bloqueado.' if r else 'Lead novo – permitido.'}")

    # Tarefa 2
    _sep("TAREFA 2 – Memoização de Comparações")
    _cache.clear()
    for lead in [lead_dup, {"nome": "Novo X", "cpf": "99999999999"}, lead_dup]:
        print(f"\n  Lead: {lead['nome']}  |  CPF: {lead['cpf']}")
        r = verificar_com_memoizacao(lead, base)
        print(f"  → {'DUPLICATA' if r else 'Lead novo'}")
    print(f"\n  Entradas no cache: {len(_cache)}")

    # Tarefa 3
    _sep("TAREFA 3 – Otimização de Agenda (Recursão)")
    with conectar() as conn:
        grade = conn.execute(
            "SELECT hora_inicio, hora_fim FROM grade_agenda "
            "WHERE tipo_agenda != 'Bloqueio' ORDER BY hora_inicio"
        ).fetchall()

    if grade:
        def hm(s): h, m = map(int, s.split(":")); return h*60+m
        slots = [(hm(r[0]), hm(r[1])) for r in grade]
        print(f"\n  Slots reais da grade ({len(slots)}):")
    else:
        slots = [(480,600),(630,720),(780,900),(930,960)]
        print("\n  Slots de exemplo (cadastre grade para usar dados reais):")

    dur = 45
    for ini, fim in slots:
        print(f"    {minutos_para_hora(ini)} – {minutos_para_hora(fim)}  ({fim-ini} min)")

    t0 = time.perf_counter()
    melhor = calcular_melhor_agenda(dur, slots)
    ms = (time.perf_counter() - t0) * 1000

    print(f"\n  Melhor agenda: {len(melhor)} consulta(s) de {dur} min")
    for k, (ini, fim) in enumerate(melhor, 1):
        print(f"    Consulta {k}: {minutos_para_hora(ini)} – {minutos_para_hora(fim)}")
    print(f"  Tempo de cálculo: {ms:.3f} ms")



#  [B] DATA SCIENCE


def menu_ds():
    if total("pacientes") == 0:
        print("\n  ⚠  Nenhum paciente cadastrado ainda.")
        print("  Cadastre pacientes antes de rodar a análise.\n")
        return

    with conectar() as conn:
        df_pac  = pd.read_sql_query("SELECT * FROM pacientes",    conn)
        df_agd  = pd.read_sql_query("SELECT * FROM agendamentos", conn)
        df_lead = pd.read_sql_query("SELECT * FROM leads",        conn)
        df_med  = pd.read_sql_query("SELECT id_medico, nome_medico FROM medicos", conn)
        df_proc = pd.read_sql_query("SELECT id_procedimento, nome_especifico FROM procedimentos", conn)
        df_msg  = pd.read_sql_query("SELECT * FROM mensagens",    conn)

    print(f"\n  Carregando análise — {len(df_pac)} paciente(s) | {len(df_agd)} agendamento(s) | {len(df_lead)} lead(s)")

    # ── Etapa 1: Preparação 
    _sep("[DS] ETAPA 1 – PREPARAÇÃO DOS DADOS")
    aus = df_pac.isnull().sum()
    aus = aus[aus > 0]
    print(f"  Registros brutos: {len(df_pac)}")
    if not aus.empty:
        print("  Valores ausentes:")
        for col, q in aus.items(): print(f"    {col}: {q}")
    else:
        print("  Sem valores ausentes.")

    df_pac = df_pac.drop_duplicates("cpf", keep="first")
    print(f"  Após remover duplicatas: {len(df_pac)}")

    if "peso" in df_pac.columns and "altura" in df_pac.columns:
        df_pac["imc"] = (df_pac["peso"] / df_pac["altura"]**2).round(2)
        print(f"  IMC calculado: {df_pac['imc'].notna().sum()} paciente(s)")

    def classe_imc(v):
        if pd.isna(v):  return "Sem dados"
        if v < 18.5:    return "Abaixo do peso"
        if v < 25.0:    return "Normal"
        if v < 30.0:    return "Sobrepeso"
        return "Obesidade"
    df_pac["classe_imc"] = df_pac["imc"].apply(classe_imc) if "imc" in df_pac.columns else "Sem dados"

    # ── Etapa 2: Análise Exploratória ────────────────────────────
    _sep("[DS] ETAPA 2 – ANÁLISE EXPLORATÓRIA")

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(
        f"Hospital São Rafael – Análise Exploratória (Sprint 3)\n"
        f"{len(df_pac)} paciente(s) | {len(df_agd)} agendamento(s) | dados reais",
        fontsize=13, weight="bold"
    )

    def sem_dados(ax, msg="Sem dados"):
        ax.text(0.5, 0.5, msg, ha="center", va="center",
                transform=ax.transAxes, fontsize=10, color="gray")

    # Status dos agendamentos
    ax = axes[0, 0]
    if not df_agd.empty:
        sc = df_agd["status"].value_counts()
        ax.bar(sc.index, sc.values, color=sns.color_palette("Set2", len(sc)))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    else:
        sem_dados(ax, "Sem agendamentos")
    ax.set_title("Status dos Agendamentos"); ax.set_ylabel("Qtd")

    # Leads por canal
    ax = axes[0, 1]
    if not df_lead.empty and df_lead["canal_origem"].notna().any():
        cc = df_lead["canal_origem"].value_counts()
        sns.barplot(x=cc.values, y=cc.index, ax=ax, palette="Greens_r")
        ax.set_xlabel("Quantidade")
    else:
        sem_dados(ax, "Sem leads com canal")
    ax.set_title("Leads por Canal de Entrada")

    # IMC
    ax = axes[0, 2]
    if "imc" in df_pac.columns and df_pac["imc"].notna().any():
        sns.histplot(df_pac["imc"].dropna(), bins=max(5, len(df_pac)//3),
                     kde=(len(df_pac) >= 5), ax=ax, color="steelblue")
        ax.set_xlabel("IMC (kg/m²)")
    else:
        sem_dados(ax, "Sem dados de peso/altura")
    ax.set_title("Distribuição de IMC")

    # Procedimentos mais agendados
    ax = axes[1, 0]
    if not df_agd.empty and not df_proc.empty:
        mg = df_agd.merge(df_proc, on="id_procedimento", how="left")
        pc = mg["nome_especifico"].value_counts().head(6)
        if not pc.empty:
            sns.barplot(x=pc.values, y=pc.index, ax=ax, palette="Blues_r")
            ax.set_xlabel("Qtd")
        else:
            sem_dados(ax)
    else:
        sem_dados(ax, "Sem agendamentos")
    ax.set_title("Procedimentos Mais Agendados")

    # Volume por médico
    ax = axes[1, 1]
    if not df_agd.empty and not df_med.empty:
        mm = df_agd.merge(df_med, on="id_medico", how="left")
        mc = mm["nome_medico"].value_counts()
        if not mc.empty:
            ax.pie(mc, labels=mc.index, autopct="%1.0f%%", startangle=140)
        else:
            sem_dados(ax)
    else:
        sem_dados(ax, "Sem dados")
    ax.set_title("Atendimentos por Médico")

    # Status dos leads
    ax = axes[1, 2]
    if not df_lead.empty:
        sl = df_lead["status_lead"].value_counts()
        cores = {"novo":"#3498db","em atendimento":"#f39c12",
                 "convertido":"#2ecc71","perdido":"#e74c3c","reagendado":"#9b59b6"}
        ax.bar(sl.index, sl.values, color=[cores.get(s,"#95a5a6") for s in sl.index])
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    else:
        sem_dados(ax, "Sem leads")
    ax.set_title("Status dos Leads"); ax.set_ylabel("Qtd")

    plt.tight_layout()
    plt.savefig("analise_exploratoria.png", dpi=150)
    plt.show()
    print("  Gráfico salvo em: analise_exploratoria.png")

    # ── Etapa 3: KPIs ────────────────────────────────────────────
    _sep("[DS] ETAPA 3 – INDICADORES DE NEGÓCIO (KPIs)")

    t_lead = len(df_lead)
    t_agd  = len(df_agd)

    conv   = (df_lead["status_lead"] == "convertido").sum() if not df_lead.empty else 0
    kpi1   = (conv / t_lead * 100) if t_lead else 0
    print(f"\n  KPI 1 – Taxa de Conversão de Leads")
    print(f"    Fórmula : (convertidos / total leads) × 100")
    print(f"    Valor   : {kpi1:.1f}%  ({conv}/{t_lead})")
    print(f"    Análise : {'Boa conversão.' if kpi1 >= 30 else 'Abaixo do esperado – revisar abordagem.'}")

    atend  = (df_agd["status"] == "atendido").sum()  if not df_agd.empty else 0
    faltas = (df_agd["status"] == "falta").sum()     if not df_agd.empty else 0
    kpi2   = (atend  / t_agd * 100) if t_agd else 0
    kpi2f  = (faltas / t_agd * 100) if t_agd else 0
    print(f"\n  KPI 2 – Taxa de Comparecimento")
    print(f"    Fórmula : (atendidos / total agendamentos) × 100")
    print(f"    Valor   : {kpi2:.1f}%  |  Faltas: {kpi2f:.1f}%")
    print(f"    Análise : {'Alta falta – acionar confirmação ativa.' if kpi2f > 15 else 'Taxa de falta aceitável.'}")

    top_procs = pd.Series(dtype=int)
    if not df_agd.empty and not df_proc.empty:
        top_procs = df_agd.merge(df_proc, on="id_procedimento", how="left")["nome_especifico"].value_counts().head(3)
    print(f"\n  KPI 3 – Procedimentos Mais Agendados (Top 3)")
    print(f"    Fórmula : contagem de agendamentos por procedimento")
    if top_procs.empty: print("    Sem dados suficientes.")
    else:
        for proc, cnt in top_procs.items():
            print(f"    {proc:<25} {cnt} agendamento(s)")
    print(f"    Análise : Orienta escala médica e insumos.")

    top_med = pd.Series(dtype=int)
    if not df_agd.empty and not df_med.empty:
        top_med = df_agd.merge(df_med, on="id_medico", how="left")["nome_medico"].value_counts()
    print(f"\n  KPI 4 – Volume por Médico")
    print(f"    Fórmula : contagem de agendamentos por médico")
    if top_med.empty: print("    Sem dados.")
    else:
        for med, cnt in top_med.items(): print(f"    {med:<28} {cnt} agendamento(s)")
    print(f"    Análise : Auxilia no balanceamento de agenda.")

    canc   = df_agd["status"].isin(["cancelado","abandono"]).sum() if not df_agd.empty else 0
    kpi5   = (canc / t_agd * 100) if t_agd else 0
    print(f"\n  KPI 5 – Taxa de Cancelamento / Abandono")
    print(f"    Fórmula : (cancelados + abandonos) / total × 100")
    print(f"    Valor   : {kpi5:.1f}%  ({canc}/{t_agd})")
    print(f"    Análise : {'Alta – revisar confirmações.' if kpi5 > 20 else 'Dentro do esperado.'}")

    # Gráfico KPIs
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Hospital São Rafael – KPIs (Sprint 3)", fontsize=13, weight="bold")
    ax = axes[0]
    if not top_procs.empty:
        sns.barplot(x=top_procs.values, y=top_procs.index, ax=ax, palette="Blues_r")
    else:
        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Procedimentos Mais Agendados"); ax.set_xlabel("Nº Agendamentos")
    ax = axes[1]
    outros = max(0, 100 - kpi1 - kpi5)
    ax.pie([kpi1, kpi5, outros],
           labels=["Leads Convertidos","Cancelados/Abandono","Outros"],
           autopct="%1.1f%%", startangle=90,
           colors=["#2ecc71","#e74c3c","#95a5a6"])
    ax.set_title("Distribuição de Status (%)")
    plt.tight_layout()
    plt.savefig("kpis_crm.png", dpi=150)
    plt.show()
    print("  Gráfico salvo em: kpis_crm.png")


# ══════════════════════════════════════════════════════════════════
#  MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def main():
    criar_tabelas()
    while True:
        t_pac  = total("pacientes")
        t_lead = total("leads")
        t_agd  = total("agendamentos")
        print(f"\n{'═'*55}")
        print(f"  🏥  HOSPITAL SÃO RAFAEL  –  Sistema Interno")
        print(f"  Pacientes: {t_pac}  |  Leads: {t_lead}  |  Agendamentos: {t_agd}")
        print(f"{'═'*55}")
        print("  1  – Médicos             (cadastrar / listar / remover)")
        print("  2  – Procedimentos       (cadastrar / listar / remover)")
        print("  3  – Colaboradores       (cadastrar / listar / login)")
        print("  ─")
        print("  4  – Pacientes           (cadastrar / buscar / listar / remover)")
        print("  5  – Leads               (visualizar / cadastrar / atualizar status)")
        print("  6  – Agendamentos        (novo / listar / atualizar status)")
        print("  7  – Grade de Agenda     (cadastrar / listar)")
        print("  8  – Orçamentos          (novo / listar / atualizar status)")
        print("  9  – SAC                 (abrir / listar / atualizar)")
        print("  10 – Pré-cirúrgico       (checklist / listar)")
        print("  11 – Histórico do Paciente")
        print("  ─")
        print("  12 – Dynamic Programming (recursão e memoização)")
        print("  13 – Data Science        (análise e KPIs)")
        print("  ─")
        print("  0  – Sair")

        op = input("\n  Escolha: ").strip()

        if   op == "1":
            sub = input("  [1] Cadastrar  [2] Listar  [3] Remover: ").strip()
            if sub == "1": cadastrar_medico()
            elif sub == "2": listar_medicos()
            elif sub == "3": remover_medico()
        elif op == "2":
            sub = input("  [1] Cadastrar  [2] Listar  [3] Remover: ").strip()
            if sub == "1": cadastrar_procedimento()
            elif sub == "2": listar_procedimentos()
            elif sub == "3": remover_procedimento()
        elif op == "3":
            sub = input("  [1] Cadastrar  [2] Listar  [3]  login  [4] Logout").strip()
            if sub == "1": cadastrar_colaborador()
            elif sub == "2": listar_colaboradores()
            elif sub == "3": login_colaborador()
            elif sub == '4': logout_colaborador_manual()
        elif op == "4":
            sub = input("  [1] Cadastrar  [2] Buscar por CPF  [3] Listar  [4] Remover: ").strip()
            if sub == "1": cadastrar_paciente()
            elif sub == "2": buscar_paciente_hospital()
            elif sub == "3": listar_pacientes()
            elif sub == "4": remover_paciente()
        elif op == "5":
            sub = input("  [1] Listar  [2] Cadastrar  [3] Atualizar status: ").strip()
            if sub == "1": listar_leads()
            elif sub == "2": cadastrar_lead()
            elif sub == "3": atualizar_status_lead()
        elif op == "6":
            sub = input("  [1] Novo  [2] Listar  [3] Atualizar status: ").strip()
            if sub == "1": cadastrar_agendamento()
            elif sub == "2": listar_agendamentos()
            elif sub == "3": atualizar_status_agendamento()
        elif op == "7":
            sub = input("  [1] Cadastrar  [2] Listar: ").strip()
            if sub == "1": cadastrar_grade()
            elif sub == "2": listar_grade()
        elif op == "8":
            sub = input("  [1] Novo  [2] Listar  [3] Atualizar status: ").strip()
            if sub == "1": cadastrar_orcamento()
            elif sub == "2": listar_orcamentos()
            elif sub == "3": atualizar_status_orcamento()
        elif op == "9":
            sub = input("  [1] Abrir  [2] Listar  [3] Atualizar: ").strip()
            if sub == "1": cadastrar_sac()
            elif sub == "2": listar_sac()
            elif sub == "3": atualizar_sac()
        elif op == "10":
            sub = input("  [1] Preencher checklist  [2] Listar todos: ").strip()
            if sub == "1": cadastrar_pre_cirurgico()
            elif sub == "2": listar_pre_cirurgico()
        elif op == "11": historico_paciente()
        elif op == "12": menu_dp()
        elif op == "13": menu_relatorios()
        elif op == "0":
            print("\n  Encerrando sistema do hospital...\n")
            break
        else:
            print("  Opção inválida.")


if __name__ == "__main__":
    main()
