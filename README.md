<!-- mcp-name: io.github.CSOAI-ORG/meok-nhvr-australia-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-nhvr-australia-mcp.html)

# meok-nhvr-australia-mcp

> Australia National Heavy Vehicle Regulator (NHVR) compliance MCP. HVNL fatigue (BFM/AFM), NHVAS modules, Chain of Responsibility, PBS, EWD, and state-specific rules. By **MEOK AI Labs**.

## Why this exists

Australia has **~200,000 heavy vehicles** under NHVR oversight across all states (excluding WA + NT for HVNL, though they mirror many rules). Operators face:

- **Chain of Responsibility (CoR)** penalties: up to **AUD 3m + 5yr prison** for company officers
- **NHVR roadside interventions** + Major Risk Category enforcement
- **NHVAS accreditation** required to access Mass/Fatigue/Maintenance concessions
- **Electronic Work Diary (EWD)** replacing paper diaries from May 2023
- **Performance-Based Standards (PBS)** approval for road-train + truck-and-dog combos

This MCP gives Compliance Managers and fleet operators a callable toolkit to **prevent** NHVR enforcement action and maintain NHVAS accreditation.

## Install

```bash
pip install meok-nhvr-australia-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "nhvr-australia": {
      "command": "meok-nhvr-australia-mcp"
    }
  }
}
```

## Tools (8)

| Tool | Use case |
|------|----------|
| `check_fatigue_management` | HVNL fatigue (Standard/BFM/AFM): 12h/24h/7d/14d rest |
| `check_nhvas_module_compliance` | NHVAS Mass / Maintenance / Fatigue audit cadence |
| `check_chain_of_responsibility` | CoR primary duties + penalty exposure |
| `check_pbs_vehicle_compliance` | PBS scheme for road-trains + truck-and-dog combos |
| `check_ewd_compliance` | Electronic Work Diary (replacing paper, May 2023) |
| `check_state_specific_rules` | NSW/VIC/QLD/SA/WA/TAS variations |
| `check_mass_management` | GVM/GCM limits, axle masses, dimension limits |
| `prepare_nhvr_audit_pack` | NHVR roadside intervention prep + Major Risk Categories |

## Pricing

- **Free** — MIT self-host
- **Starter** — AUD 49/mo
- **Pro** — AUD 149/mo (multi-driver)
- **Fleet** — AUD 999/mo (50+ trucks, NHVAS audit-export)

## Regulatory basis

- **Heavy Vehicle National Law (HVNL)** — applies in NSW, VIC, QLD, SA, TAS, ACT (WA/NT mirror most rules)
- **NHVR Heavy Vehicle Accreditation Scheme (NHVAS)** — Mass, Maintenance, Fatigue modules
- **Chain of Responsibility (CoR)** — primary duties (HVNL Part 1A)
- **Performance-Based Standards (PBS) scheme** — National Heavy Vehicle Accreditation
- **Electronic Work Diary (EWD)** — mandated from May 2023 (paper still allowed in transition)
- **Fatigue Management** — Standard Hours (no accreditation) / BFM / AFM tiers

## Sign your responses

```bash
export MEOK_HMAC_SECRET="your-secret"
meok-nhvr-australia-mcp
```

## License

MIT (c) 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)


<!-- GEO-FOOTER:v1 -->

---

### Part of the MEOK constellation

This MCP is one node in a connected ecosystem built by **MEOK AI LABS** around a single
sovereign AI core — governed agents with a hash-chained audit trail, mapped to the CSOAI
compliance charter.

- 🌐 The whole map: **<https://meok.ai/constellation>**
- 🛡️ AI governance & certification: **<https://councilof.ai>** · **<https://csoai.org>**
- ✅ Verify any signed report: **<https://meok.ai/verify>**
