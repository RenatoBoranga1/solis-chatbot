from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

import httpx
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIAnalysis, AuditLog, Conversation, Handoff, Lead, Message, Proposal, Ticket
from app.schemas import DashboardAIInsights
from app.services.ai_prompts import AI_ANALYSIS_SYSTEM_PROMPT
from app.services.intent import classify_intent, normalize
from app.services.rag import KnowledgeService
from app.services.severity import is_electrical_risk

logger = logging.getLogger(__name__)

AnalysisPayload = dict[str, Any]

IRRITATION_TERMS = ["cansado", "ninguem resolve", "ninguém resolve", "procon", "processo", "reclame aqui", "absurdo"]
FINANCING_TERMS = ["financiamento", "financiar", "parcelar", "banco"]
TECHNICAL_TERMS = ["inversor", "erro", "gerando", "monitoramento", "wifi", "wi-fi", "disjuntor", "aplicativo"]
RISK_TERMS = ["cheiro de queimado", "faisca", "faísca", "fumaca", "fumaça", "choque", "curto", "muito quente"]


class AIAnalysisService:
    def __init__(self, db: Session, actor_user_id: str | None = None):
        self.db = db
        self.actor_user_id = actor_user_id
        self.knowledge = KnowledgeService(db)

    def analyze_conversation(self, conversation_id: str) -> AIAnalysis:
        conversation = self._require(Conversation, conversation_id, "Conversation not found")
        lead = self._lead_for_conversation(conversation_id)
        ticket = self._ticket_for_conversation(conversation_id)
        fallback = self._rule_conversation_analysis(conversation, lead, ticket)
        payload = self._maybe_generative_analysis(self._conversation_context(conversation, lead, ticket), fallback)
        return self._persist_analysis(
            analysis_type="conversation",
            payload=payload,
            conversation_id=conversation.id,
            lead_id=lead.id if lead else None,
            ticket_id=ticket.id if ticket else None,
        )

    def analyze_lead(self, lead_id: str) -> AIAnalysis:
        lead = self._require(Lead, lead_id, "Lead not found")
        conversation = self.db.get(Conversation, lead.conversation_id) if lead.conversation_id else None
        proposal = self._proposal_for_lead(lead.id)
        fallback = self._rule_lead_analysis(lead, conversation, proposal)
        payload = self._maybe_generative_analysis(self._lead_context(lead, conversation, proposal), fallback)
        return self._persist_analysis(
            analysis_type="lead",
            payload=payload,
            conversation_id=lead.conversation_id,
            lead_id=lead.id,
        )

    def analyze_ticket(self, ticket_id: str) -> AIAnalysis:
        ticket = self._require(Ticket, ticket_id, "Ticket not found")
        conversation = self.db.get(Conversation, ticket.conversation_id) if ticket.conversation_id else None
        fallback = self._rule_ticket_analysis(ticket, conversation)
        payload = self._maybe_generative_analysis(self._ticket_context(ticket, conversation), fallback)
        return self._persist_analysis(
            analysis_type="ticket",
            payload=payload,
            conversation_id=ticket.conversation_id,
            ticket_id=ticket.id,
        )

    def generate_suggested_reply(self, conversation_id: str) -> str:
        existing = self.get_latest_conversation_analysis(conversation_id)
        if existing:
            return existing.suggested_reply
        return self.analyze_conversation(conversation_id).suggested_reply

    def generate_daily_insights(self) -> DashboardAIInsights:
        total_conversations = self.db.scalar(select(func.count(Conversation.id))) or 0
        handoffs = self.db.scalar(select(func.count(Conversation.id)).where(Conversation.transferred_to_human.is_(True))) or 0
        leads = list(self.db.scalars(select(Lead).order_by(desc(Lead.created_at)).limit(500)).all())
        tickets = list(self.db.scalars(select(Ticket).order_by(desc(Ticket.created_at)).limit(500)).all())
        conversations = list(self.db.scalars(select(Conversation).order_by(desc(Conversation.created_at)).limit(500)).all())

        hot_leads = sum(1 for lead in leads if self._lead_score(lead, None) >= 75)
        critical_tickets = sum(1 for ticket in tickets if self._ticket_risk_score(ticket, None) >= 85)
        irritated = sum(1 for conversation in conversations if self._sentiment(self._conversation_text(conversation)) == "irritado")
        financing = sum(1 for lead in leads if bool(lead.financing_interest) or self._contains(lead.notes or "", FINANCING_TERMS))
        recurring_problems = self._top_values([ticket.problem_type for ticket in tickets if ticket.problem_type], limit=5)
        main_reasons = self._top_values([conversation.intent or "nao_classificado" for conversation in conversations], limit=5)
        cities = self._top_values(
            [
                str((lead.extra or {}).get("city") or (lead.extra or {}).get("city_state") or "")
                for lead in leads
                if lead.extra
            ],
            limit=5,
        )

        recommendations = self._management_recommendations(
            hot_leads=hot_leads,
            critical_tickets=critical_tickets,
            financing=financing,
            recurring_problems=recurring_problems,
            irritated=irritated,
        )
        return DashboardAIInsights(
            leads_quentes=hot_leads,
            chamados_criticos=critical_tickets,
            clientes_irritados=irritated,
            oportunidades_financiamento=financing,
            problemas_tecnicos_recorrentes=recurring_problems,
            principais_motivos=main_reasons,
            principais_cidades=cities,
            taxa_handoff=round((handoffs / total_conversations) * 100, 2) if total_conversations else 0.0,
            recomendacoes=recommendations,
        )

    def get_latest_conversation_analysis(self, conversation_id: str) -> AIAnalysis | None:
        return self._latest_analysis("conversation", conversation_id=conversation_id)

    def get_latest_lead_analysis(self, lead_id: str) -> AIAnalysis | None:
        return self._latest_analysis("lead", lead_id=lead_id)

    def get_latest_ticket_analysis(self, ticket_id: str) -> AIAnalysis | None:
        return self._latest_analysis("ticket", ticket_id=ticket_id)

    def _rule_conversation_analysis(
        self,
        conversation: Conversation,
        lead: Lead | None,
        ticket: Ticket | None,
    ) -> AnalysisPayload:
        text = self._conversation_text(conversation)
        intent = conversation.intent or classify_intent(text).name
        sentiment = self._sentiment(text)
        technical_risk = self._technical_risk(text, conversation.severity, ticket)
        urgency = self._urgency(conversation.severity, technical_risk, sentiment)
        lead_score = self._lead_score(lead, conversation) if lead else self._conversation_commercial_score(intent, text)
        risk_score = self._ticket_risk_score(ticket, conversation) if ticket else self._conversation_risk_score(text, conversation.severity)
        priority_score = max(lead_score, risk_score, self._urgency_score(urgency))
        missing_data = self._conversation_missing_data(conversation, lead, ticket, intent)
        commercial_opportunity = self._commercial_opportunity(intent, lead_score)
        conversion_probability = self._probability_from_score(lead_score)
        next_action = self._conversation_next_action(intent, urgency, missing_data, lead, ticket)
        summary = self._conversation_summary(conversation, intent, urgency, sentiment)
        suggested_reply = self._suggested_reply(intent, urgency, missing_data, technical_risk)
        media_action, media_reply = self._multimedia_recommendation(text, technical_risk)
        if media_action:
            next_action = f"{next_action} {media_action}"
        if media_reply:
            suggested_reply = f"{suggested_reply}\n\n{media_reply}"
        tags = self._tags(intent, sentiment, urgency, commercial_opportunity, technical_risk)
        return self._sanitize_payload(
            {
                "executive_summary": summary,
                "customer_intent": intent,
                "customer_sentiment": sentiment,
                "urgency_level": urgency,
                "commercial_opportunity": commercial_opportunity,
                "conversion_probability": conversion_probability,
                "technical_risk": technical_risk,
                "priority_score": priority_score,
                "missing_data": missing_data,
                "recommended_next_action": next_action,
                "suggested_reply": suggested_reply,
                "tags": tags,
                "raw_analysis": {
                    "mode": "rules",
                    "lead_score": lead_score,
                    "risk_score": risk_score,
                    "conversation_status": conversation.status,
                    "handoff": bool(conversation.transferred_to_human),
                },
            }
        )

    def _rule_lead_analysis(self, lead: Lead, conversation: Conversation | None, proposal: Proposal | None = None) -> AnalysisPayload:
        score = self._lead_score(lead, conversation)
        probability = self._probability_from_score(score)
        missing_data = self._lead_missing_data(lead)
        opportunity = "alta" if score >= 75 else "media" if score >= 45 else "baixa"
        next_action = "Solicitar a conta de energia e encaminhar para proposta comercial." if missing_data else "Encaminhar para proposta comercial."
        if lead.financing_interest:
            next_action = "Priorizar contato comercial e apresentar possibilidades de financiamento após análise da conta."
        if score >= 75 and not missing_data:
            next_action = "Gerar proposta comercial como rascunho e revisar valores, condições técnicas e comerciais antes do envio."
        suggested_reply = (
            "Ola! Ja temos as informacoes iniciais para avancar com sua analise. "
            "Para deixar a proposta mais precisa, pode enviar uma foto ou PDF da sua conta de energia?"
        )
        tags = ["lead", f"lead_{self._lead_label(score)}", f"conversao_{probability}"]
        raw_analysis = {"mode": "rules", "lead_score": score, "financing_interest": bool(lead.financing_interest)}
        if proposal and proposal.recommended_kit_name:
            next_action = (
                f"Validar o kit recomendado ({proposal.recommended_kit_name}) antes do envio, confirmando conta de energia, "
                "tipo de telhado, area disponivel, sombreamento, padrao de entrada e condicoes comerciais."
            )
            suggested_reply = (
                "Perfeito. A equipe ja consegue preparar uma pre-proposta com kit recomendado, mas vamos revisar os dados "
                "tecnicos e comerciais antes de confirmar valores ou dimensionamento final."
            )
            tags.extend(["kit_recomendado", normalize(proposal.recommended_kit_name).replace(" ", "_")])
            raw_analysis.update(
                {
                    "recommended_kit_id": proposal.recommended_kit_id,
                    "recommended_kit_name": proposal.recommended_kit_name,
                    "kit_selection_reason": proposal.kit_selection_reason,
                }
            )
        summary = (
            f"Lead com score {score}/100 e chance {probability} de conversão. "
            "Os dados coletados permitem abordagem comercial objetiva."
        )
        return self._sanitize_payload(
            {
                "executive_summary": summary,
                "customer_intent": "orcamento",
                "customer_sentiment": self._sentiment(self._conversation_text(conversation) if conversation else lead.notes or ""),
                "urgency_level": "media" if score >= 75 else "baixa",
                "commercial_opportunity": opportunity,
                "conversion_probability": probability,
                "technical_risk": "baixo",
                "priority_score": score,
                "missing_data": missing_data,
                "recommended_next_action": next_action,
                "suggested_reply": suggested_reply,
                "tags": tags + (["gerar_proposta_comercial"] if score >= 75 and not missing_data else []),
                "raw_analysis": raw_analysis,
            }
        )

    def _rule_ticket_analysis(self, ticket: Ticket, conversation: Conversation | None) -> AnalysisPayload:
        score = self._ticket_risk_score(ticket, conversation)
        urgency = "critica" if score >= 85 else "alta" if score >= 60 else "media" if score >= 35 else "baixa"
        risk = "critico" if score >= 85 else "alto" if score >= 60 else "medio" if score >= 35 else "baixo"
        missing_data = self._ticket_missing_data(ticket)
        risk_text = self._conversation_text(conversation) if conversation else ticket.technical_notes or ""
        action = (
            "Acionar técnico imediatamente e orientar o cliente a não mexer no equipamento."
            if risk in {"critico", "alto"} or is_electrical_risk(risk_text)
            else "Manter em triagem técnica e solicitar os dados faltantes antes de agendar visita."
        )
        return self._sanitize_payload(
            {
                "executive_summary": f"Chamado técnico com risco {score}/100 e prioridade {urgency}.",
                "customer_intent": "suporte_tecnico",
                "customer_sentiment": self._sentiment(risk_text),
                "urgency_level": urgency,
                "commercial_opportunity": "baixa",
                "conversion_probability": "baixa",
                "technical_risk": risk,
                "priority_score": score,
                "missing_data": missing_data,
                "recommended_next_action": action,
                "suggested_reply": self._ticket_suggested_reply(risk, missing_data),
                "tags": ["chamado_tecnico", f"risco_{risk}", f"prioridade_{urgency}"],
                "raw_analysis": {"mode": "rules", "risk_score": score, "ticket_status": ticket.status},
            }
        )

    def _persist_analysis(
        self,
        analysis_type: str,
        payload: AnalysisPayload,
        conversation_id: str | None = None,
        lead_id: str | None = None,
        ticket_id: str | None = None,
    ) -> AIAnalysis:
        analysis = AIAnalysis(
            conversation_id=conversation_id,
            lead_id=lead_id,
            ticket_id=ticket_id,
            analysis_type=analysis_type,
            executive_summary=payload["executive_summary"],
            customer_intent=payload["customer_intent"],
            customer_sentiment=payload["customer_sentiment"],
            urgency_level=payload["urgency_level"],
            commercial_opportunity=payload["commercial_opportunity"],
            conversion_probability=payload["conversion_probability"],
            technical_risk=payload["technical_risk"],
            priority_score=int(payload["priority_score"]),
            missing_data=list(payload.get("missing_data") or []),
            recommended_next_action=payload["recommended_next_action"],
            suggested_reply=payload["suggested_reply"],
            tags=list(payload.get("tags") or []),
            raw_analysis=dict(payload.get("raw_analysis") or {}),
        )
        self.db.add(analysis)
        self.db.flush()
        self.db.add(
            AuditLog(
                actor_user_id=self.actor_user_id,
                action="ai_analysis.generated",
                entity_type=analysis_type,
                entity_id=conversation_id or lead_id or ticket_id,
                details={
                    "analysis_id": analysis.id,
                    "priority_score": analysis.priority_score,
                    "urgency_level": analysis.urgency_level,
                },
            )
        )
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def _latest_analysis(
        self,
        analysis_type: str,
        conversation_id: str | None = None,
        lead_id: str | None = None,
        ticket_id: str | None = None,
    ) -> AIAnalysis | None:
        statement = select(AIAnalysis).where(AIAnalysis.analysis_type == analysis_type)
        if conversation_id:
            statement = statement.where(AIAnalysis.conversation_id == conversation_id)
        if lead_id:
            statement = statement.where(AIAnalysis.lead_id == lead_id)
        if ticket_id:
            statement = statement.where(AIAnalysis.ticket_id == ticket_id)
        return self.db.scalar(statement.order_by(desc(AIAnalysis.created_at)).limit(1))

    def _maybe_generative_analysis(self, context: dict[str, Any], fallback: AnalysisPayload) -> AnalysisPayload:
        if not settings.enable_generative_ai or not settings.openai_api_key or settings.ai_provider != "openai":
            return fallback

        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": AI_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                    ],
                },
                timeout=8.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            generated = json.loads(content)
            generated["raw_analysis"] = {
                **dict(generated.get("raw_analysis") or {}),
                "mode": "generative",
                "provider": "openai",
                "model": settings.ai_model,
            }
            return self._normalize_generated_payload(generated, fallback)
        except Exception as exc:
            logger.warning("ai_analysis_generation_failed", extra={"error_type": type(exc).__name__})
            return fallback

    def _normalize_generated_payload(self, generated: dict[str, Any], fallback: AnalysisPayload) -> AnalysisPayload:
        normalized = dict(fallback)
        for key in [
            "executive_summary",
            "customer_intent",
            "customer_sentiment",
            "urgency_level",
            "commercial_opportunity",
            "conversion_probability",
            "technical_risk",
            "recommended_next_action",
            "suggested_reply",
        ]:
            if generated.get(key):
                normalized[key] = str(generated[key])
        if isinstance(generated.get("priority_score"), int | float):
            normalized["priority_score"] = max(0, min(100, int(generated["priority_score"])))
        if isinstance(generated.get("missing_data"), list):
            normalized["missing_data"] = [str(item) for item in generated["missing_data"][:20]]
        if isinstance(generated.get("tags"), list):
            normalized["tags"] = [normalize(str(item)).replace(" ", "_") for item in generated["tags"][:12]]
        normalized["raw_analysis"] = dict(generated.get("raw_analysis") or fallback.get("raw_analysis") or {})
        return self._sanitize_payload(normalized)

    def _conversation_context(
        self,
        conversation: Conversation,
        lead: Lead | None,
        ticket: Ticket | None,
    ) -> dict[str, Any]:
        return {
            "conversation": {
                "id": conversation.id,
                "channel": conversation.channel,
                "status": conversation.status,
                "intent": conversation.intent,
                "severity": conversation.severity,
                "summary": self._mask_sensitive(conversation.summary or ""),
                "collected_data": self._mask_json(conversation.collected_data or {}),
                "messages": [
                    {"sender_type": message.sender_type, "content": self._mask_sensitive(message.content)}
                    for message in self._messages(conversation)[-20:]
                ],
            },
            "lead": self._mask_json(self._lead_brief(lead)) if lead else None,
            "ticket": self._mask_json(self._ticket_brief(ticket)) if ticket else None,
        }

    def _lead_context(self, lead: Lead, conversation: Conversation | None, proposal: Proposal | None = None) -> dict[str, Any]:
        return {
            "lead": self._mask_json(self._lead_brief(lead)),
            "proposal": self._mask_json(self._proposal_brief(proposal)) if proposal else None,
            "conversation": self._conversation_context(conversation, lead, None) if conversation else None,
        }

    def _ticket_context(self, ticket: Ticket, conversation: Conversation | None) -> dict[str, Any]:
        return {"ticket": self._mask_json(self._ticket_brief(ticket)), "conversation": self._conversation_context(conversation, None, ticket) if conversation else None}

    def _lead_brief(self, lead: Lead | None) -> dict[str, Any]:
        if not lead:
            return {}
        return {
            "id": lead.id,
            "property_type": lead.property_type,
            "average_bill": float(lead.average_bill) if lead.average_bill is not None else None,
            "utility_company": lead.utility_company,
            "roof_type": lead.roof_type,
            "financing_interest": lead.financing_interest,
            "status": lead.status,
            "notes": lead.notes,
            "extra": lead.extra or {},
        }

    def _ticket_brief(self, ticket: Ticket | None) -> dict[str, Any]:
        if not ticket:
            return {}
        return {
            "id": ticket.id,
            "problem_type": ticket.problem_type,
            "severity": ticket.severity,
            "status": ticket.status,
            "technical_notes": ticket.technical_notes,
            "extra": ticket.extra or {},
        }

    def _proposal_brief(self, proposal: Proposal | None) -> dict[str, Any]:
        if not proposal:
            return {}
        return {
            "id": proposal.id,
            "status": proposal.status,
            "recommended_kit_id": proposal.recommended_kit_id,
            "recommended_kit_name": proposal.recommended_kit_name,
            "kit_selection_reason": proposal.kit_selection_reason,
            "estimated_system_power_kwp": float(proposal.estimated_system_power_kwp)
            if proposal.estimated_system_power_kwp is not None
            else None,
            "estimated_monthly_generation_kwh": float(proposal.estimated_monthly_generation_kwh)
            if proposal.estimated_monthly_generation_kwh is not None
            else None,
            "total_amount": float(proposal.total_amount) if proposal.total_amount is not None else None,
        }

    def _conversation_text(self, conversation: Conversation | None) -> str:
        if not conversation:
            return ""
        parts = [conversation.summary or ""]
        parts.extend(message.content for message in self._messages(conversation))
        parts.extend(str(value) for value in (conversation.collected_data or {}).values() if isinstance(value, str))
        return self._mask_sensitive(" ".join(parts))

    @staticmethod
    def _messages(conversation: Conversation) -> list[Message]:
        messages = list(getattr(conversation, "messages", []) or [])
        return sorted(messages, key=lambda message: message.created_at)

    def _lead_for_conversation(self, conversation_id: str) -> Lead | None:
        return self.db.scalar(select(Lead).where(Lead.conversation_id == conversation_id).order_by(desc(Lead.created_at)).limit(1))

    def _ticket_for_conversation(self, conversation_id: str) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.conversation_id == conversation_id).order_by(desc(Ticket.created_at)).limit(1))

    def _proposal_for_lead(self, lead_id: str) -> Proposal | None:
        return self.db.scalar(select(Proposal).where(Proposal.lead_id == lead_id).order_by(desc(Proposal.created_at)).limit(1))

    def _sentiment(self, text: str) -> str:
        normalized = normalize(text)
        if self._contains(normalized, RISK_TERMS):
            return "urgente"
        if self._contains(normalized, IRRITATION_TERMS):
            return "irritado"
        if self._contains(normalized, ["problema", "erro", "parou", "preocupado", "nao gera", "não gera"]):
            return "preocupado"
        if self._contains(normalized, ["obrigado", "perfeito", "quero instalar", "orcamento", "orçamento"]):
            return "positivo"
        return "neutro"

    def _technical_risk(self, text: str, severity: str | None, ticket: Ticket | None) -> str:
        if is_electrical_risk(text) or self._contains(text, RISK_TERMS):
            return "critico"
        if severity == "alta" or (ticket and ticket.severity == "alta"):
            return "alto"
        if severity == "media" or (ticket and ticket.severity == "media") or self._contains(text, TECHNICAL_TERMS):
            return "medio"
        return "baixo"

    @staticmethod
    def _urgency(severity: str | None, technical_risk: str, sentiment: str) -> str:
        if technical_risk == "critico":
            return "critica"
        if severity == "alta" or technical_risk == "alto" or sentiment in {"irritado", "urgente"}:
            return "alta"
        if severity == "media" or technical_risk == "medio":
            return "media"
        return "baixa"

    @staticmethod
    def _urgency_score(urgency: str) -> int:
        return {"critica": 95, "alta": 78, "media": 52, "baixa": 20}.get(urgency, 20)

    def _conversation_commercial_score(self, intent: str, text: str) -> int:
        score = 25 if intent in {"orcamento", "viabilidade", "financiamento", "comercial"} else 10
        if self._contains(text, FINANCING_TERMS):
            score += 20
        if self._contains(text, ["conta", "valor", "economia", "instalar"]):
            score += 20
        return min(100, score)

    def _conversation_risk_score(self, text: str, severity: str | None) -> int:
        score = {"alta": 65, "media": 38, "baixa": 10}.get(severity or "baixa", 10)
        if is_electrical_risk(text) or self._contains(text, RISK_TERMS):
            score += 35
        if self._contains(text, IRRITATION_TERMS):
            score += 20
        return min(100, score)

    def _lead_score(self, lead: Lead | None, conversation: Conversation | None) -> int:
        if not lead:
            return self._conversation_commercial_score(conversation.intent or "", self._conversation_text(conversation)) if conversation else 0
        extra = lead.extra or {}
        text = " ".join(str(value) for value in extra.values() if isinstance(value, str))
        score = 10
        if lead.average_bill:
            score += 25
        if extra.get("city") or extra.get("city_state"):
            score += 15
        if lead.property_type or extra.get("property_type"):
            score += 15
        if lead.utility_company or extra.get("utility_company"):
            score += 10
        if lead.financing_interest or self._contains(text, FINANCING_TERMS):
            score += 15
        if extra.get("has_energy_bill") or extra.get("attachments") or extra.get("energy_bill_extraction_id"):
            score += 15
        if extra.get("average_consumption_kwh") or extra.get("current_consumption_kwh"):
            score += 10
        if self._contains(text + " " + (lead.notes or ""), ["urgente", "quero instalar", "fechar", "proposta"]):
            score += 10
        return min(100, score)

    def _ticket_risk_score(self, ticket: Ticket | None, conversation: Conversation | None) -> int:
        if not ticket:
            return self._conversation_risk_score(self._conversation_text(conversation), conversation.severity if conversation else None)
        text = " ".join(
            [
                ticket.problem_type or "",
                ticket.technical_notes or "",
                " ".join(str(value) for value in (ticket.extra or {}).values() if isinstance(value, str)),
                self._conversation_text(conversation),
            ]
        )
        score = {"alta": 55, "media": 30, "baixa": 15}.get(ticket.severity or "baixa", 15)
        if is_electrical_risk(text) or self._contains(text, RISK_TERMS):
            score += 40
        if self._contains(text, ["totalmente parado", "sistema parado", "inversor desligado", "sem geracao", "sem geração"]):
            score += 25
        if self._contains(text, IRRITATION_TERMS):
            score += 20
        if self._contains(text, ["comercio", "comércio", "industria", "indústria", "prejuizo", "prejuízo"]):
            score += 15
        return min(100, score)

    def _conversation_missing_data(
        self,
        conversation: Conversation,
        lead: Lead | None,
        ticket: Ticket | None,
        intent: str,
    ) -> list[str]:
        if lead or intent in {"orcamento", "viabilidade", "financiamento", "comercial"}:
            return self._lead_missing_data(lead, conversation.collected_data or {})
        if ticket or intent in {"suporte_tecnico", "problema_inversor", "baixa_geracao", "erro_monitoramento", "wifi_inversor"}:
            return self._ticket_missing_data(ticket, conversation.collected_data or {})
        return ["contexto do atendimento"] if not conversation.summary and not self._messages(conversation) else []

    def _lead_missing_data(self, lead: Lead | None, collected: dict[str, Any] | None = None) -> list[str]:
        collected = collected or {}
        missing = []
        if not (lead and lead.average_bill) and not collected.get("average_bill"):
            missing.append("conta de energia")
        if not collected.get("city_state") and not collected.get("city"):
            missing.append("cidade")
        if not (lead and lead.property_type) and not collected.get("property_type"):
            missing.append("tipo de imóvel")
        if not (lead and lead.utility_company) and not collected.get("utility_company"):
            missing.append("distribuidora")
        if not (
            collected.get("has_energy_bill")
            or collected.get("attachments")
            or collected.get("energy_bill_extraction_id")
            or collected.get("average_consumption_kwh")
        ):
            missing.append("foto ou PDF da conta de luz")
        if not collected.get("best_contact_time"):
            missing.append("melhor horário de contato")
        return missing

    def _ticket_missing_data(self, ticket: Ticket | None, collected: dict[str, Any] | None = None) -> list[str]:
        collected = collected or (ticket.extra if ticket else {}) or {}
        missing = []
        checks = {
            "foto ou print do problema": collected.get("attachments") or collected.get("app_print"),
            "modelo do inversor": collected.get("inverter_model"),
            "mensagem de erro": collected.get("error_message"),
            "endereço da instalação": collected.get("installation_address"),
            "data de início": collected.get("started_at"),
            "evento recente": collected.get("recent_event"),
            "status de geração": collected.get("generation_status"),
        }
        for label, value in checks.items():
            if not value:
                missing.append(label)
        return missing

    def _commercial_opportunity(self, intent: str, lead_score: int) -> str:
        if lead_score >= 75:
            return "alta"
        if lead_score >= 45 or intent in {"orcamento", "viabilidade", "financiamento", "comercial"}:
            return "media"
        return "baixa"

    @staticmethod
    def _probability_from_score(score: int) -> str:
        if score >= 75:
            return "alta"
        if score >= 45:
            return "media"
        return "baixa"

    @staticmethod
    def _lead_label(score: int) -> str:
        if score >= 75:
            return "quente"
        if score >= 45:
            return "morno"
        return "frio"

    def _conversation_next_action(
        self,
        intent: str,
        urgency: str,
        missing_data: list[str],
        lead: Lead | None,
        ticket: Ticket | None,
    ) -> str:
        if urgency in {"critica", "alta"} and ticket:
            return "Priorizar suporte técnico humano e orientar segurança do cliente."
        if ticket:
            return "Solicitar dados técnicos faltantes e manter chamado em triagem."
        if lead or intent in {"orcamento", "viabilidade", "financiamento", "comercial"}:
            if missing_data:
                return f"Solicitar {missing_data[0]} e encaminhar para o comercial."
            return "Encaminhar para proposta comercial."
        if intent == "humano":
            return "Assumir atendimento humano e revisar histórico antes de responder."
        return "Responder dúvida simples ou encaminhar para especialista se a base não cobrir o tema."

    def _conversation_summary(self, conversation: Conversation, intent: str, urgency: str, sentiment: str) -> str:
        base = conversation.summary or "Atendimento iniciado pelo Solis com dados ainda parciais."
        return self._mask_sensitive(
            f"Cliente com intenção principal '{intent}', sentimento {sentiment} e urgência {urgency}. {base}"
        )

    @staticmethod
    def _suggested_reply(intent: str, urgency: str, missing_data: list[str], technical_risk: str) -> str:
        if technical_risk in {"critico", "alto"} or urgency in {"critica", "alta"}:
            return (
                "Obrigado por avisar. Por segurança, não mexa no equipamento, cabos, disjuntores ou inversor. "
                "Vou priorizar seu atendimento com a equipe técnica da Solar Soluções."
            )
        if intent in {"orcamento", "viabilidade", "financiamento", "comercial"}:
            if missing_data:
                return f"Perfeito. Para avançarmos com uma análise mais precisa, pode me enviar {missing_data[0]}?"
            return "Perfeito. Já temos as informações iniciais e vamos encaminhar sua análise ao comercial."
        return "Entendi. Vou registrar essas informações e indicar o melhor próximo passo com a equipe da Solar Soluções."

    @staticmethod
    def _ticket_suggested_reply(risk: str, missing_data: list[str]) -> str:
        if risk in {"critico", "alto"}:
            return (
                "Obrigado pelas informações. Por segurança, não mexa no equipamento até avaliação técnica. "
                "Vamos priorizar o encaminhamento do seu chamado."
            )
        if missing_data:
            return f"Obrigado. Para completar a triagem técnica, pode enviar {missing_data[0]}?"
        return "Obrigado pelas informações. Seu chamado será mantido em triagem técnica para o próximo encaminhamento."

    @staticmethod
    def _tags(intent: str, sentiment: str, urgency: str, opportunity: str, risk: str) -> list[str]:
        return [
            normalize(intent).replace(" ", "_"),
            f"sentimento_{sentiment}",
            f"urgencia_{urgency}",
            f"oportunidade_{opportunity}",
            f"risco_{risk}",
        ]

    def _management_recommendations(
        self,
        hot_leads: int,
        critical_tickets: int,
        financing: int,
        recurring_problems: list[str],
        irritated: int,
    ) -> list[str]:
        recommendations = []
        if recurring_problems:
            recommendations.append(
                f"Criar resposta padrão e tutorial para reduzir contatos recorrentes sobre {recurring_problems[0]}."
            )
        if financing:
            recommendations.append("Reforçar no fluxo comercial a importância da conta de energia para análise de financiamento.")
        if critical_tickets:
            recommendations.append("Revisar diariamente chamados críticos e priorizar casos com risco elétrico.")
        if irritated:
            recommendations.append("Acompanhar atendimentos com cliente irritado para evitar escalonamento reputacional.")
        if hot_leads:
            recommendations.append("Priorizar leads quentes no mesmo dia para aumentar conversão comercial.")
        return recommendations or ["Manter revisão semanal da base de conhecimento e dos principais motivos de contato."]

    def _multimedia_recommendation(self, text: str, technical_risk: str) -> tuple[str | None, str | None]:
        if technical_risk in {"critico", "alto"} or is_electrical_risk(text):
            return None, None
        article = self.knowledge.find_matching_article(text)
        if not article:
            return None, None

        action_parts = []
        reply_parts = []
        if article.send_video_with_answer and article.video_url:
            video_title = article.video_title or "vídeo oficial da Solar Soluções"
            action_parts.append(f"Enviar vídeo oficial sobre {video_title}.")
            reply_parts.extend(["Vídeo recomendado:", video_title, article.video_url])
        if article.send_resource_with_answer and article.resource_url:
            resource_title = article.resource_title or "material oficial da Solar Soluções"
            action_parts.append(f"Enviar material de apoio: {resource_title}.")
            if reply_parts:
                reply_parts.append("")
            reply_parts.extend(["Material de apoio:", resource_title, article.resource_url])
        return " ".join(action_parts) or None, "\n".join(reply_parts) or None

    @staticmethod
    def _top_values(values: list[str], limit: int = 5) -> list[str]:
        clean_values = [value.strip() for value in values if value and value.strip()]
        return [value for value, _count in Counter(clean_values).most_common(limit)]

    @staticmethod
    def _contains(text: str, terms: list[str]) -> bool:
        normalized = normalize(text)
        return any(normalize(term) in normalized for term in terms)

    def _sanitize_payload(self, payload: AnalysisPayload) -> AnalysisPayload:
        clean = dict(payload)
        for key in [
            "executive_summary",
            "recommended_next_action",
            "suggested_reply",
            "customer_intent",
            "customer_sentiment",
            "urgency_level",
            "commercial_opportunity",
            "conversion_probability",
            "technical_risk",
        ]:
            clean[key] = self._mask_sensitive(str(clean.get(key) or ""))
        clean["priority_score"] = max(0, min(100, int(clean.get("priority_score") or 0)))
        clean["missing_data"] = [self._mask_sensitive(str(item)) for item in list(clean.get("missing_data") or [])]
        clean["tags"] = [normalize(str(item)).replace(" ", "_") for item in list(clean.get("tags") or [])]
        clean["raw_analysis"] = self._mask_json(dict(clean.get("raw_analysis") or {}))
        return clean

    def _mask_json(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._mask_json(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._mask_json(item) for item in value]
        if isinstance(value, str):
            return self._mask_sensitive(value)
        return value

    @staticmethod
    def _mask_sensitive(value: str) -> str:
        masked = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email mascarado]", value)
        masked = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento mascarado]", masked)
        masked = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "[documento mascarado]", masked)
        masked = re.sub(r"\b(?:\d[\s().-]?){8,}\b", "[dado mascarado]", masked)
        return masked

    def _require(self, model, item_id: str, message: str):
        item = self.db.get(model, item_id)
        if not item:
            raise ValueError(message)
        return item
