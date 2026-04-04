#  Sistema de Gestão Hospitalar com Programação Dinâmica e Data Science

##  Descrição do Projeto

Este projeto consiste no desenvolvimento de um sistema interno para gestão hospitalar, com foco em cadastro, organização e análise de dados de pacientes, leads e agendamentos.

Além das funcionalidades de CRUD (Create, Read, Update, Delete), o sistema incorpora conceitos avançados de:

* **Programação Dinâmica**
* **Data Science aplicada a CRM**

O objetivo é simular um ambiente real de hospital, utilizando algoritmos e análise de dados para apoiar decisões estratégicas.

---

##  Funcionalidades Implementadas

###  Gestão de Pacientes

* Cadastro de pacientes
* Validação de dados (CPF e e-mail únicos)
* Cálculo automático de IMC
* Busca e listagem

---

###  Gestão de Leads (CRM)

* Cadastro de leads

* Controle de status:

  * novo
  * em atendimento
  * convertido
  * perdido
  * reagendado

* Associação com:

  * procedimento
  * médico
  * colaborador

---

###  Agendamentos

* Criação de consultas
* Controle de status
* Integração com grade de horários

---

###  Banco de Dados

* SQLite
* Estrutura relacional com tabelas:

  * pacientes
  * leads
  * médicos
  * colaboradores
  * agendamentos
  * grade_agenda
  * orçamentos
  * sac

---

#  Programação Dinâmica

O sistema implementa conceitos fundamentais de otimização e eficiência computacional.

---

## 🔹 1. Verificação Recursiva de Duplicidade

Função:

* `verificar_duplicidade_recursivo`

Descrição:

* Percorre a lista de cadastros de forma recursiva
* Verifica duplicidade por CPF ou nome

Complexidade:

* O(n)

Objetivo:

* Demonstrar uso de recursão em busca linear

---

## 🔹 2. Memoização (Cache de Comparações)

Funções:

* `comparar_com_cache`
* `verificar_com_memoizacao`

Descrição:

* Armazena resultados de comparações já realizadas
* Evita cálculos repetidos

Diferencial:

* Uso de chave ordenada → `(a,b) == (b,a)`

Benefício:

* Redução de custo computacional

---

## 🔹 3. Otimização de Agenda Médica

Função:

* `calcular_melhor_agenda`

Descrição:

* Algoritmo recursivo com backtracking
* Maximiza o número de consultas em horários disponíveis

Entrada:

* Slots de tempo
* Duração fixa de consulta

Saída:

* Melhor combinação sem sobreposição

Objetivo:

* Simular um problema real de otimização hospitalar

---

#  Data Science aplicada ao CRM

##  Objetivo

Extrair insights a partir dos dados do sistema para melhorar decisões e eficiência operacional.

---

##  Fonte de dados

Tabela analisada:

* `leads`

Campos principais:

* `canal_origem`
* `status_lead`
* `data_entrada`

---

##  Análises realizadas

###  Leads por canal

Agrupamento por origem:

* Instagram
* Google
* Facebook
* TikTok
* Indicação

📌 Identifica os canais mais eficientes

---

###  Taxa de conversão

[
\text{Taxa} = \frac{\text{Convertidos}}{\text{Total}} \times 100
]

 Mede a eficiência do atendimento

---

### 3️ Distribuição de status

* novo
* em atendimento
* convertido
* perdido
* reagendado

 Identifica gargalos no funil

---

##  Visualização

Gráfico gerado com matplotlib:

```python
plt.savefig("kpis_crm.png", dpi=150)
```

Arquivo gerado:

* `kpis_crm.png`

Mostra a distribuição percentual dos leads.

---

##  Tecnologias Utilizadas

* Python 3
* SQLite
* Matplotlib
* SQL

---


##  Como Executar

1. Clone o repositório:

```bash
git clone <seu-repositorio>
```

2. Execute o sistema:

```bash
python hospital.py
```

3. Utilize o menu interativo no terminal

---

##  Exemplo de Saída

```
[DP] DYNAMIC PROGRAMMING

TAREFA 1 – Verificação Recursiva
→ Lead novo – permitido
→ DUPLICATA – bloqueado

TAREFA 2 – Memoização
→ CACHE MISS
→ CACHE HIT

TAREFA 3 – Otimização de Agenda
→ Melhor agenda: 6 consultas
```

---

##  Diferenciais do Projeto

* Integração de algoritmos com banco de dados
* Aplicação prática de teoria
* Estrutura modular (db + lógica)
* Uso de:

  * recursão
  * memo4ização
  * análise de dados

---

## Autores

* Belton Lee
* Erik Kaiyu
* Guilherme Vital
* Kayque Carvalho
* Lucas Guerreiro

---

