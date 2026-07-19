# Competitive map — what Clearance is *not*

## Do not reinvent

| Project | Role | Clearance stance |
| --- | --- | --- |
| [agentgateway](https://github.com/agentgateway/agentgateway) (~3.9k★, LF) | LLM + MCP + A2A gateway | Optional dependency later |
| [humanlayer/agentcontrolplane](https://github.com/humanlayer/agentcontrolplane) | K8s Agent Control Plane | Outer-loop scheduling is their job |
| [jamjet-labs/jamjet](https://github.com/jamjet-labs/jamjet) | Action-control plane (policy, durable HITL, audit) | Optional policy layer later |
| LangGraph / OpenAI Agents SDK | Orchestration engines | Phase 1: code graph; Phase 2: adapter |
| Langfuse / Laminar / AgentOps | Observability | Phase 2 export |
| Harbor (harborframework.com) | **Agent eval harness** | Different product — **name collision avoided** |

## Commercial AP / IDP (do not claim displacement)

Vic.ai, BILL, Rossum, Tipalti, Coupa, Stampli, Yooz, Basware, …  
Clearance uses **invoice DocOps as a demo vertical** that hiring managers understand, not as a funded attack on their moats.

## Clearance wedge

1. **Production agent engineering showcase** (patterns from Anthropic / Magentic-One / MCP)  
2. **Quality proof** (gold evals, confidence gates, published metrics)  
3. **HITL + irreversible action gates + audit**  
4. **Open kit** others can reuse for document cases  

**Sentence:**  
Agentgateway connects · HumanLayer schedules · JamJet polices · LangGraph runs · **Clearance finishes the business case.**
