import requests
import json
import logging

logger = logging.getLogger(__name__)

from logic.llm_client import KaggleClient

class MessageGenerator:
    def __init__(self, llm_url="https://edef-35-197-119-224.ngrok-free.app"):
        self.client = KaggleClient(base_url=llm_url)

    def generate_campaign(self, profile_data, my_offering, context_prospects=None, variant_mode=False):
        """
        Generates 5-channel outreach messages based on the analyzed profile.
        If context_prospects is provided, uses them as "success stories".
        If variant_mode is True, generates an alternative "B" version.
        """
        
        context_str = ""
        if context_prospects:
            company_raw = profile_data.get('company') if isinstance(profile_data, dict) else ''
            target_company = (company_raw or '').lower()
            
            # Build domain-aware social proof using match reasons from KB
            direct_refs = []   # Same company — strongest
            peer_refs = []     # Same career stage / college — bootcamp relevant
            industry_refs = [] # Same industry / similar role — general
            
            for p in context_prospects[:3]:
                name = p.get('name', 'someone')
                role = p.get('role', 'a professional')
                company = p.get('company', '')
                reasons = p.get('_match_reasons', [])
                
                if 'same_company' in reasons:
                    direct_refs.append({'name': name, 'role': role, 'company': company})
                elif 'similar_career_stage' in reasons or 'similar_skills' in reasons:
                    peer_refs.append({'name': name, 'role': role, 'company': company})
                elif 'same_industry' in reasons or 'similar_role' in reasons:
                    industry_refs.append({'name': name, 'role': role, 'company': company})
            
            parts = []
            
            # TIER 1: Same company = must reference
            if direct_refs:
                ref = direct_refs[0]
                parts.append(
                    f"DIRECT REFERENCE (USE THIS): We previously worked with "
                    f"{ref['name']} ({ref['role']}) at {ref['company']}. "
                    f"You MUST naturally mention this in email and LinkedIn — e.g., "
                    f"'We recently collaborated with {ref['name']} from your team at {ref['company']}...' or "
                    f"'Your colleague {ref['name']} already uses our solution...'. "
                    f"Keep it warm and natural."
                )
            
            # TIER 2: Same career stage / college = peer reference (bootcamp-style)
            if peer_refs:
                names = [f"{p['name']} ({p['company']})" if p['company'] and p['company'] != 'Unknown' 
                         else p['name'] for p in peer_refs]
                names_str = ", ".join(names)
                parts.append(
                    f"PEER REFERENCE (USE THIS): Students/professionals at a similar stage — "
                    f"{names_str} — have already benefited from our offering. "
                    f"You should reference this naturally — e.g., "
                    f"'Your batchmate {peer_refs[0]['name']} recently joined our program...' or "
                    f"'Students from {peer_refs[0].get('company', 'your college')} have found success with us...'. "
                    f"Make it feel relatable, like a peer recommendation."
                )
            
            # TIER 3: Same industry / similar role = soft reference
            if industry_refs:
                names = [f"{p['name']} ({p['role']} at {p['company']})" for p in industry_refs 
                         if p['company'] and p['company'] != 'Unknown']
                if names:
                    names_str = ", ".join(names)
                    parts.append(
                        f"SOFT REFERENCE (optional): Professionals in similar roles — "
                        f"{names_str} — have connected with us. "
                        f"Mention subtly if relevant, e.g., 'Engineers at {industry_refs[0]['company']} have used our platform...'."
                    )
            
            if parts:
                context_str = "\nSOCIAL PROOF FROM KNOWLEDGE BASE:\n" + "\n".join(parts)

        variant_instruction = ""
        if variant_mode:
            variant_instruction = "IMPORTANT: This is an A/B test variant. Try a DIFFERENT angle than usual (e.g., if you usually lead with value, lead with a question, or be more direct)."

        system_prompt = f"""
        You are a world-class SDR and Copywriter.
        Your task is to generate hyper-personalized outreach messages that feel warm and well-researched.
        
        OFFERING CONTEXT:
        "{my_offering}"
        
        CRITICAL RULES:
        1. MESSAGE LENGTH: ALL platform messages (LinkedIn, WhatsApp, SMS, Instagram) MUST be 4-5 lines minimum (not counting greeting/signature).
           - Each message should be comprehensive and compelling. Do NOT generate 1-liners.
        2. NO FLUFF: Don't just list facts. Weave them into a narrative. 
        3. INTEGRATION: You must fluidly bridge the prospect's specific details (pain points, recent activity) with the 'OFFERING CONTEXT'. Do not just paste the offering; explain *why* it matters to *them*.
        4. TONE: Professional yet conversational.
        5. CALL TO ACTION: Clear next step.
        {context_str}
        """

        example_profile = json.dumps({
            "name": "Sarah Jones",
            "company": "CloudScale",
            "role": "VP Marketing",
            "education": ["MBA, Stanford"],
            "certifications": ["Google Analytics"],
            "recent_activity": ["Posted about AI in Marketing"],
            "psychological_profile": {"pain_points": ["Scaling growth", "Data overload"]},
            "key_insights": ["Loves hiking"],
            "personalization_hooks": ["Mention Stanford", "Discuss AI post"]
        }, indent=2)

        example_output = json.dumps({
            "email": {
                "subject": "Thoughts on your AI post + Stanford connection?",
                "body": "Hi Sarah,\n\nI was just reading your recent post about AI in Marketing - couldn't agree more about the need for automation. It's clear you're forward-thinking.\n\nNoticed you're a Stanford MBA grad as well (impressive program). That rigorous analytical background really shows in your strategic approach.\n\nGiven your focus on scaling growth at CloudScale and handling data overload, our AI-driven talent platform can help you build the right team to execute that vision without the headache.\n\nWould you be open to a quick chat next Tuesday about how we can support your scaling efforts?"
            },
            "linkedin": "Hi Sarah, loved your thoughts on AI in Marketing. As a fellow data-nerd (saw your Google Analytics cert!), I wanted to connect.\n\nI see you're tackling growth scaling at CloudScale. It's a tough challenge, but crucial.",
            "whatsapp": "Hi Sarah, saw your post on AI. We're building something similar for scaling teams...\n\nYour background at Stanford suggests you value high-leverage tools. Our platform aligns perfectly with that philosophy.\n\nWe help leaders like you cut through the noise and find top-tier talent instantly.\n\nWould love to send over a case study if you're interested? Let me know!",
            "sms": "Sarah, quick question about your AI post. It really resonated with our team's mission.\n\nWe specialize in helping VPs like you scale growth without the burnout.\n\nGiven your focus on efficiency, I think our solution could be a game-changer for CloudScale.\n\nFree for a 5-min call this week to discuss strategies?",
            "instagram": "Hey Sarah, huge fan of your content on AI - it's spot on!\n\nI noticed you're also into hiking; that's awesome. We believe in work-life balance too.\n\nAt our core, we help marketing leaders automate the heavy lifting so they can focus on strategy (and trails!).\n\nCheck out our link if you need help scaling your team effectively.",
            "analysis": {
                "personalization_score": "9.5/10",
                "reasoning": "weaved in post + education + certs naturally."
            }
        }, indent=2)

        user_prompt = f"""
        EXAMPLE INPUT PROFILE:
        {example_profile}
        
        EXAMPLE JSON OUTPUT:
        {example_output}
        
        REAL INPUT PROFILE:
        {json.dumps(profile_data, indent=2)}
        
        REAL JSON OUTPUT:
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response_text = self.client.chat(messages)
            
            json_res = self.client.extract_json(response_text)
            if json_res:
                return json_res

            # Fallback or return raw text if that's what we got (though analyzer expects dict)
            return {"error": "Failed to parse JSON response", "raw_response": response_text}
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"error": str(e)}
