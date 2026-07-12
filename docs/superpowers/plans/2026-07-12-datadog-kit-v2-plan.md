# Datadog RCA Kit - V2 Plan (2026-07-12)

Baseado em aprendizado real: monitors ✅ (29), logs ✅ (precisa query específica), metrics ❌ (sem host), events ❌ (ServiceException SDK).

## Tasks (sequential)

### T1: Monitors como trigger
Monitors alertando → extrair `host`, `service` das tags → injetar como contexto nas queries de logs/spans.
- `collector.py`: `_list_monitors` retorna `MonitorsResult` → extrair tags únicas (`host:*, service:*`)
- `fetch_all`: primeiro buscar monitors → se alertando, usar tags pra refinar logs/spans queries
- Test: validar parsing de `tags: list[str]` → `dict[str, str]`

### T2: APM Spans
Novo sinal `spans` via SDK v2 `SpansApi.search_spans()`.
- `collector.py`: `_search_spans()` — query `@duration:>1s`, sort `-@duration`
- `models.py`: `SpanEntry`, `SpansResult`
- `fetch_all`: incluir 5° sinal em paralelo
- Test: validar sem dados reais (graceful)

### T3: Diagnosis LLM real
Substituir fallback por LLM real (OpenAI via `instructor` para structured output).
- Instalar `openai`, `instructor` (ou httpx direto OpenAI API)
- `settings.py`: adicionar `OPENAI_API_KEY`
- `diagnosis.py`: `_call_llm()` async com httpx, retry
- Prompt improvements: incluir spans, evidência específica
- Test: mock httpx, validar parse

### T4: RCA completo
`RcaDiagnosis` com dados reais: `evidence_refs` com IDs de monitors/logs/postmortems.
- `router.py`: `evidence_refs` com `{monitors:[{id,name,state}], logs:[timestamps]}`
- `remediation_steps` baseado em monitors (descrição + query)
- `causal_chain` com eventos e timestamps reais
- `summary` gerado por LLM (não hardcoded)

### T5: Incident link
`incident_id` opcional na request → busca incidente Datadog → contextualiza diagnosis.
- `client.py`: `get_incident(incident_id)` via `IncidentsApi`
- `router.py`: se `incident_id` na request, busca incidente, popula contexto no prompt
- Test: mock incidents API

### T6: Teste e2e
`curl POST /api/v1/datadog/investigate` com dados reais → validar fields do RCA.
- Script `scripts/test_v2.sh` que POST e valida JSON schema
- Verificar: `evidence_refs` não vazio, `causal_chain` populado, `remediation_steps` não vazio

## Deps to add
- `openai` (ou httpx direto)
- `httpx` (já pode existir — verificar)
