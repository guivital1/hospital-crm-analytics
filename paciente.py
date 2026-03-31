"""
paciente.py – Portal do Paciente – Hospital São Rafael
Challenge FIAP – Engenharia de Software 2º Ano | Sprint 3

Perfil: Paciente (autoatendimento)
Funcionalidades:
  • Criar conta e fazer login
  • Ver e atualizar seus próprios dados
  • Solicitar agendamento (escolher procedimento e médico)
  • Consultar histórico de agendamentos e orçamentos
  • Abrir SAC (reclamação)
  • Ver mensagens recebidas
  • Ver checklist pré-cirúrgico

Execute:
    python3 paciente.py

Dependências: nenhuma além da biblioteca padrão do Python
"""

import sqlite3
from datetime import datetime, timedelta

from db import (
    criar_tabelas, conectar, parse_data, total, imc_str,
    buscar_paciente_cpf, buscar_paciente_email,
    listar_medicos_resumo, listar_procedimentos_resumo, imprimir_paciente
)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# ══════════════════════════════════════════════════════════════════
#  SESSÃO DO PACIENTE
# ══════════════════════════════════════════════════════════════════

_sessao: dict | None = None   # guarda dados do paciente logado


def _logado() -> bool:
    return _sessao is not None


def _pid() -> int:
    return _sessao["id_paciente"]


def _sep(titulo=""):
    print(f"\n{'─'*50}")
    if titulo:
        print(f"  {titulo}")
        print(f"{'─'*50}")


# ══════════════════════════════════════════════════════════════════
#  AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════════

def criar_conta():
    _sep("Criar Conta")
    nome   = input("  Nome completo: ").strip()
    cpf    = input("  CPF (somente números): ").strip()
    email  = input("  E-mail: ").strip()
    senha  = input("  Crie uma senha: ").strip()
    tel    = input("  Telefone (WhatsApp): ").strip()
    sexo   = input("  Sexo (M/F/O): ").strip().upper()
    nasc   = input("  Data de nascimento (DD/MM/AAAA): ").strip()
    peso_t = input("  Peso em kg (ex: 72.5 – opcional): ").strip()
    alt_t  = input("  Altura em m (ex: 1.68 – opcional): ").strip()

    if not nome or not cpf or not email or not senha or not nasc:
        print("  ✗ Campos obrigatórios faltando.")
        return False

    try:
        peso   = float(peso_t) if peso_t else None
        altura = float(alt_t)  if alt_t  else None
    except ValueError:
        print("  ✗ Peso ou altura inválidos.")
        return False

    if peso and altura:
        print(f"  ℹ IMC calculado: {peso/altura**2:.2f}")

    entrada = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        with conectar() as conn:
            conn.execute(
                "INSERT INTO pacientes (nome_completo, cpf, email, senha, telefone, sexo, "
                "data_nascimento, peso, altura, entrada) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (nome, cpf, email, senha, tel or None, sexo or None, nasc, peso, altura, entrada)
            )
        print("  ✓ Conta criada com sucesso! Faça login para continuar.")
        return True
    except sqlite3.IntegrityError:
        print("  ✗ CPF ou e-mail já cadastrado.")
        return False


def login():
    global _sessao
    _sep("Login")
    email = input("  E-mail: ").strip()
    senha = input("  Senha: ").strip()

    row = buscar_paciente_email(email)
    if not row:
        print("  ✗ E-mail não encontrado.")
        return False

    with conectar() as conn:
        res = conn.execute(
            "SELECT senha FROM pacientes WHERE email=?", (email,)
        ).fetchone()

    if not res or res[0] != senha:
        print("  ✗ Senha incorreta.")
        return False

    _sessao = {
        "id_paciente": row[0],
        "nome":        row[1],
        "cpf":         row[2],
        "email":       row[3],
        "telefone":    row[4],
        "sexo":        row[5],
        "data_nasc":   row[6],
        "peso":        row[7],
        "altura":      row[8],
    }
    print(f"\n  ✓ Bem-vindo(a), {_sessao['nome']}!")
    return True


def logout():
    global _sessao
    _sessao = None
    print("  ✓ Sessão encerrada.")


# ══════════════════════════════════════════════════════════════════
#  MEUS DADOS
# ══════════════════════════════════════════════════════════════════

def ver_meus_dados():
    _sep("Meus Dados")
    row = buscar_paciente_cpf(_sessao["cpf"])
    if row:
        imprimir_paciente(row)


def atualizar_meus_dados():
    _sep("Atualizar Meus Dados")
    s = _sessao
    print("  Deixe em branco para manter o valor atual.")

    novo_tel  = input(f"  Telefone [{s['telefone'] or '-'}]: ").strip() or s["telefone"]
    novo_peso = input(f"  Peso [{s['peso'] or '-'}]: ").strip()
    nova_alt  = input(f"  Altura [{s['altura'] or '-'}]: ").strip()
    nova_senha = input("  Nova senha (ou Enter para manter): ").strip()

    try:
        peso   = float(novo_peso) if novo_peso else s["peso"]
        altura = float(nova_alt)  if nova_alt  else s["altura"]
    except ValueError:
        print("  ✗ Peso ou altura inválidos.")
        return

    with conectar() as conn:
        if nova_senha:
            conn.execute(
                "UPDATE pacientes SET telefone=?, peso=?, altura=?, senha=? WHERE id_paciente=?",
                (novo_tel, peso, altura, nova_senha, _pid())
            )
        else:
            conn.execute(
                "UPDATE pacientes SET telefone=?, peso=?, altura=? WHERE id_paciente=?",
                (novo_tel, peso, altura, _pid())
            )

    # Atualiza sessão
    _sessao["telefone"] = novo_tel
    _sessao["peso"]     = peso
    _sessao["altura"]   = altura

    imc = imc_str(peso, altura)
    print(f"  ✓ Dados atualizados.{' IMC: '+imc if imc != '-' else ''}")


# ══════════════════════════════════════════════════════════════════
#  AGENDAMENTOS
# ══════════════════════════════════════════════════════════════════

def solicitar_agendamento():
    _sep("Solicitar Agendamento")

    # Lista procedimentos e médicos disponíveis
    procs = listar_procedimentos_resumo()
    meds  = listar_medicos_resumo()

    if not procs:
        print("  ✗ Nenhum procedimento disponível ainda.")
        return
    if not meds:
        print("  ✗ Nenhum médico disponível ainda.")
        return

    print("\n  Procedimentos disponíveis:")
    for pid, nome, valor in procs:
        v = f"  –  R$ {valor:.2f}" if valor else ""
        print(f"    [{pid}] {nome}{v}")

    print("\n  Médicos disponíveis:")
    for mid, nome, espec in meds:
        print(f"    [{mid}] {nome}  –  {espec or '-'}")

    id_proc = input("\n  ID do procedimento desejado: ").strip()
    id_med  = input("  ID do médico de preferência: ").strip()
    data_h  = input("  Data e hora desejada (DD/MM/AAAA HH:MM): ").strip()

    if not id_proc.isdigit() or not id_med.isdigit():
        print("  ✗ IDs inválidos.")
        return
    dt = parse_data(data_h)
    if not dt:
        print("  ✗ Data/hora inválida. Use o formato DD/MM/AAAA HH:MM")
        return

    with conectar() as conn:
        conn.execute(
            "INSERT INTO agendamentos (id_paciente, id_medico, id_procedimento, data_hora, status, origem) "
            "VALUES (?,?,?,?,'agendado','CRM')",
            (_pid(), int(id_med), int(id_proc), dt.strftime("%Y-%m-%d %H:%M:%S"))
        )
    print("  ✓ Agendamento solicitado! Aguarde confirmação do hospital.")


def meus_agendamentos():
    _sep("Meus Agendamentos")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT a.id_agendamento, m.nome_medico, pr.nome_especifico, "
            "a.data_hora, a.status "
            "FROM agendamentos a "
            "JOIN medicos m ON a.id_medico=m.id_medico "
            "JOIN procedimentos pr ON a.id_procedimento=pr.id_procedimento "
            "WHERE a.id_paciente=? ORDER BY a.data_hora", (_pid(),)
        ).fetchall()

    if not rows:
        print("  Nenhum agendamento encontrado.")
        return

    status_emoji = {
        "agendado": "🔵", "atendido": "✅", "falta": "❌",
        "cancelado": "🚫", "reagendado": "🟠", "abandono": "⚫"
    }
    for aid, med, proc, dt, status in rows:
        emoji = status_emoji.get(status, "⚪")
        print(f"\n  {emoji} [{aid}]  {proc}")
        print(f"       Médico: {med}")
        print(f"       Data: {dt}  |  Status: {status}")


def cancelar_agendamento():
    _sep("Cancelar Agendamento")
    meus_agendamentos()
    aid = input("\n  ID do agendamento para cancelar: ").strip()
    if not aid.isdigit():
        print("  ✗ ID inválido.")
        return
    with conectar() as conn:
        n = conn.execute(
            "UPDATE agendamentos SET status='cancelado' "
            "WHERE id_agendamento=? AND id_paciente=? AND status='agendado'",
            (int(aid), _pid())
        ).rowcount
    print("  ✓ Agendamento cancelado." if n else "  ✗ Não foi possível cancelar (verifique o ID e o status).")


# ══════════════════════════════════════════════════════════════════
#  ORÇAMENTOS
# ══════════════════════════════════════════════════════════════════

def meus_orcamentos():
    _sep("Meus Orçamentos")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT o.id_orcamento, m.nome_medico, pr.nome_especifico, "
            "o.valor_total, o.status_orc, o.data_criacao "
            "FROM orcamentos o "
            "JOIN medicos m ON o.id_medico=m.id_medico "
            "JOIN procedimentos pr ON o.id_procedimento=pr.id_procedimento "
            "WHERE o.id_paciente=? ORDER BY o.data_criacao DESC", (_pid(),)
        ).fetchall()

    if not rows:
        print("  Nenhum orçamento encontrado.")
        return

    status_emoji = {
        "aberto": "🔵", "em andamento": "🟡",
        "fechado": "✅", "encerrado": "🔴"
    }
    for oid, med, proc, valor, status, data in rows:
        emoji = status_emoji.get(status, "⚪")
        print(f"\n  {emoji} [{oid}]  {proc}")
        print(f"       Médico: {med}  |  Valor: R$ {valor:.2f}")
        print(f"       Status: {status}  |  Data: {data}")


# ══════════════════════════════════════════════════════════════════
#  SAC
# ══════════════════════════════════════════════════════════════════

def abrir_sac():
    _sep("Abrir Reclamação (SAC)")
    motivo = input("  Descreva o problema: ").strip()
    if not motivo:
        print("  ✗ Descrição obrigatória.")
        return
    prazo = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        conn.execute(
            "INSERT INTO sac (id_paciente, motivo, prazo_limite, status_solucao) VALUES (?,?,?,'pendente')",
            (_pid(), motivo, prazo)
        )
    print(f"  ✓ Reclamação registrada. Prazo de resposta: {prazo}")


def meu_sac():
    _sep("Minhas Reclamações (SAC)")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_sac, motivo, status_solucao, prazo_limite, data_abertura "
            "FROM sac WHERE id_paciente=? ORDER BY data_abertura DESC", (_pid(),)
        ).fetchall()
    if not rows:
        print("  Nenhuma reclamação registrada.")
        return
    status_emoji = {"pendente": "⏳", "em tratativa": "🔄", "resolvido": "✅"}
    for sid, motivo, status, prazo, abertura in rows:
        emoji = status_emoji.get(status, "⚪")
        print(f"\n  {emoji} Protocolo #{sid}  |  {status}")
        print(f"       Motivo: {motivo}")
        print(f"       Abertura: {abertura}  |  Prazo: {prazo}")


# ══════════════════════════════════════════════════════════════════
#  MENSAGENS RECEBIDAS
# ══════════════════════════════════════════════════════════════════

def minhas_mensagens():
    _sep("Mensagens Recebidas")
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id_msg, tipo_canal, tipo_gatilho, data_envio "
            "FROM mensagens WHERE id_paciente=? ORDER BY data_envio DESC", (_pid(),)
        ).fetchall()
    if not rows:
        print("  Nenhuma mensagem registrada.")
        return
    canal_emoji = {"WhatsApp": "💬", "SMS": "📱", "E-mail": "📧"}
    for mid, canal, gatilho, data in rows:
        emoji = canal_emoji.get(canal, "📩")
        print(f"  {emoji} [{mid}]  {canal}  –  {gatilho or '-'}  |  {data}")


# ══════════════════════════════════════════════════════════════════
#  PRÉ-CIRÚRGICO
# ══════════════════════════════════════════════════════════════════

def meu_pre_cirurgico():
    _sep("Meu Checklist Pré-Cirúrgico")
    with conectar() as conn:
        row = conn.execute(
            "SELECT status_imc, exames_completos, checklist_ok, autorizacao_med "
            "FROM pre_cirurgico WHERE id_paciente=? ORDER BY id_pre DESC LIMIT 1", (_pid(),)
        ).fetchone()
    if not row:
        print("  Nenhum checklist registrado ainda.\n  Aguarde o hospital preencher após sua consulta.")
        return
    imc, exam, chk, aut = row
    ok = lambda v: "✅" if v else "❌"
    apto = all([imc, exam, chk, aut])
    print(f"\n  IMC aprovado     : {ok(imc)}")
    print(f"  Exames completos : {ok(exam)}")
    print(f"  Checklist ok     : {ok(chk)}")
    print(f"  Autorização méd. : {ok(aut)}")
    print(f"\n  Situação: {'✅ APTO para cirurgia!' if apto else '⚠  PENDENTE – itens acima ainda não aprovados.'}")


# ══════════════════════════════════════════════════════════════════
#  MENU DO PACIENTE LOGADO
# ══════════════════════════════════════════════════════════════════

def menu_paciente():
    while True:
        nome = _sessao["nome"].split()[0]
        print(f"\n{'═'*50}")
        print(f"  👤  Olá, {nome}!")
        print(f"{'═'*50}")
        print("  1 – Meus dados")
        print("  2 – Atualizar meus dados")
        print("  ─")
        print("  3 – Solicitar agendamento")
        print("  4 – Meus agendamentos")
        print("  5 – Cancelar agendamento")
        print("  ─")
        print("  6 – Meus orçamentos")
        print("  7 – Abrir reclamação (SAC)")
        print("  8 – Minhas reclamações")
        print("  9 – Mensagens recebidas")
        print("  10– Checklist pré-cirúrgico")
        print("  ─")
        print("  0 – Sair / Logout")

        op = input("\n  Escolha: ").strip()

        if   op == "1":  ver_meus_dados()
        elif op == "2":  atualizar_meus_dados()
        elif op == "3":  solicitar_agendamento()
        elif op == "4":  meus_agendamentos()
        elif op == "5":  cancelar_agendamento()
        elif op == "6":  meus_orcamentos()
        elif op == "7":  abrir_sac()
        elif op == "8":  meu_sac()
        elif op == "9":  minhas_mensagens()
        elif op == "10": meu_pre_cirurgico()
        elif op == "0":
            logout()
            break
        else:
            print("  Opção inválida.")


# ══════════════════════════════════════════════════════════════════
#  MENU PRINCIPAL (pré-login)
# ══════════════════════════════════════════════════════════════════

def main():
    criar_tabelas()
    while True:
        print(f"\n{'═'*50}")
        print("  🏥  HOSPITAL SÃO RAFAEL  –  Portal do Paciente")
        print(f"{'═'*50}")
        print("  1 – Login")
        print("  2 – Criar conta")
        print("  0 – Sair")

        op = input("\n  Escolha: ").strip()

        if op == "1":
            if login():
                menu_paciente()
        elif op == "2":
            criar_conta()
        elif op == "0":
            print("\n  Até logo!\n")
            break
        else:
            print("  Opção inválida.")


if __name__ == "__main__":
    main()
