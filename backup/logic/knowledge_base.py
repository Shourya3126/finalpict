import json
import os
import uuid
from datetime import datetime

class KnowledgeBase:
    def __init__(self, file_path="knowledge_base.json"):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def load_all(self):
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def save_prospect(self, profile_data, messages=None, url=""):
        """
        Save a prospect with full profile, generated messages, URL, and timestamp.
        Updates existing entry if same name+company found, otherwise appends.
        """
        data = self.load_all()
        
        entry = {
            "id": str(uuid.uuid4()),
            "name": profile_data.get("name", "Unknown"),
            "company": profile_data.get("company", "Unknown"),
            "role": profile_data.get("role", "Unknown"),
            "industry": profile_data.get("industry", "Unknown"),
            "seniority": profile_data.get("seniority", "Unknown"),
            "summary": self._build_summary(profile_data),
            "profile": profile_data,
            "messages": messages or {},
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if exists (by name + company)
        for i, p in enumerate(data):
            if (p.get("name", "").lower() == entry["name"].lower() and 
                p.get("company", "").lower() == entry["company"].lower()):
                entry["id"] = p.get("id", entry["id"])  # Keep original ID
                data[i] = entry
                break
        else:
            data.append(entry)
            
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return entry["id"]

    def delete_prospect(self, prospect_id):
        """Delete a prospect by ID."""
        data = self.load_all()
        data = [p for p in data if p.get("id") != prospect_id]
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def find_similar(self, company=None, industry=None, role=None, offering=""):
        """
        Find similar prospects, with matching logic adapted to the offering type.
        - Bootcamp/course: prioritize education, career stage, skills overlap
        - Talent/hiring: prioritize company, role seniority
        - Dev tool: prioritize company, tech stack
        Returns up to 3 matches with match_reason attached.
        """
        data = self.load_all()
        if not data:
            return []
        
        offering_type = self._detect_offering_type(offering)
        
        scored = []
        for p in data:
            score = 0
            reasons = []
            
            p_company = p.get("company", "").lower()
            p_role = p.get("role", "").lower()
            p_industry = p.get("industry", "").lower()
            
            # === UNIVERSAL: Exact company match is always valuable ===
            if company and p_company == company.lower():
                score += 4
                reasons.append("same_company")
            
            # === OFFERING-SPECIFIC SCORING ===
            if offering_type == "bootcamp":
                # Students/early-career at same college = strong match
                edu_keywords = ["student", "sophomore", "junior", "senior", "freshman", 
                                "intern", "trainee", "graduate", "university", "institute", 
                                "college", "vit", "iit", "nit"]
                if any(kw in p_role for kw in edu_keywords):
                    score += 2
                    reasons.append("similar_career_stage")
                
                # Role keyword overlap (e.g., both are "developers" or "engineers")
                if role and p.get("role"):
                    role_words = set(role.lower().split())
                    p_role_words = set(p_role.split())
                    overlap = role_words & p_role_words - {"at", "the", "and", "of", "in"}
                    if overlap:
                        score += 1
                        reasons.append("similar_skills")
            
            elif offering_type == "talent":
                # Same industry = strong match for hiring
                if industry and p_industry == industry.lower():
                    score += 3
                    reasons.append("same_industry")
                
                # Similar role level
                if role and p.get("role"):
                    role_words = set(role.lower().split())
                    p_role_words = set(p_role.split())
                    overlap = role_words & p_role_words - {"at", "the", "and", "of", "in"}
                    if overlap:
                        score += 2
                        reasons.append("similar_role")
            
            elif offering_type == "devtool":
                # Same industry
                if industry and p_industry == industry.lower():
                    score += 2
                    reasons.append("same_industry")
                
                # Role overlap (same type of engineer)
                if role and p.get("role"):
                    role_words = set(role.lower().split())
                    p_role_words = set(p_role.split())
                    overlap = role_words & p_role_words - {"at", "the", "and", "of", "in"}
                    if overlap:
                        score += 1
                        reasons.append("similar_role")
            
            else:
                # Fallback: original scoring
                if industry and p_industry == industry.lower():
                    score += 2
                    reasons.append("same_industry")
                if role and p.get("role"):
                    role_words = set(role.lower().split())
                    p_role_words = set(p_role.split())
                    if role_words & p_role_words:
                        score += 1
                        reasons.append("similar_role")
            
            if score > 0:
                p_with_reason = dict(p)
                p_with_reason["_match_reasons"] = reasons
                scored.append((score, reasons, p_with_reason))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[2] for item in scored[:3]]

    def _detect_offering_type(self, offering):
        """
        Detect the offering type from the offering text.
        Returns: 'bootcamp', 'talent', 'devtool', or 'general'
        """
        if not offering:
            return "general"
        
        text = offering.lower()
        
        bootcamp_keywords = ["bootcamp", "course", "training", "learn", "student", 
                             "placement", "interview prep", "mentorship", "campus",
                             "certification", "workshop", "curriculum", "teaching"]
        talent_keywords = ["hire", "hiring", "talent", "recruit", "staffing", 
                          "developer", "engineer", "team", "scale", "on-demand",
                          "vetted", "pre-vetted", "join", "joining", "career",
                          "opportunity", "opening", "vacancy"]
        devtool_keywords = ["tool", "platform", "saas", "product", "software", 
                           "deploy", "ci/cd", "code review", "integration", 
                           "automate", "workflow", "api"]
        
        bootcamp_score = sum(1 for kw in bootcamp_keywords if kw in text)
        talent_score = sum(1 for kw in talent_keywords if kw in text)
        devtool_score = sum(1 for kw in devtool_keywords if kw in text)
        
        max_score = max(bootcamp_score, talent_score, devtool_score)
        if max_score == 0:
            return "general"
        
        if bootcamp_score == max_score:
            return "bootcamp"
        elif talent_score == max_score:
            return "talent"
        else:
            return "devtool"

    def get_context_string(self, similar_prospects):
        """
        Build a natural-language context string for the generator prompt.
        References specific names, roles, and companies from past outreach.
        """
        if not similar_prospects:
            return ""
        
        refs = []
        for p in similar_prospects[:3]:
            name = p.get("name", "someone")
            role = p.get("role", "a professional")
            company = p.get("company", "")
            if company and company != "Unknown":
                refs.append(f"{name} ({role} at {company})")
            else:
                refs.append(f"{name} ({role})")
        
        ref_str = ", ".join(refs)
        return (
            f"\nSOCIAL PROOF CONTEXT: We have previously connected with "
            f"professionals in similar roles — {ref_str}. "
            f"You may subtly reference this social proof if it fits naturally "
            f"(e.g., 'We recently worked with engineers at [Company]...'). "
            f"Do NOT force it if it doesn't fit the conversation flow."
        )

    def _build_summary(self, profile_data):
        """Build a short text summary from profile data."""
        parts = []
        role = profile_data.get("role", "")
        company = profile_data.get("company", "")
        if role and role != "Unknown":
            parts.append(role)
        if company and company != "Unknown":
            parts.append(f"at {company}")
        
        insights = profile_data.get("key_insights", [])
        if insights:
            parts.append(f"— {', '.join(insights[:2])}")
        
        return " ".join(parts) if parts else "No summary"

    def get_stats(self):
        """Return basic stats about the knowledge base."""
        data = self.load_all()
        companies = set(p.get("company", "") for p in data if p.get("company") and p.get("company") != "Unknown")
        industries = set(p.get("industry", "") for p in data if p.get("industry") and p.get("industry") != "Unknown")
        return {
            "total": len(data),
            "companies": len(companies),
            "industries": len(industries)
        }
