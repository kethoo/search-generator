import os
import streamlit as st
from openai import OpenAI
import json
import re
from file_extractors import extract_text_from_file
from dotenv import load_dotenv

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Multi-Platform Job Search Generator", layout="wide")

st.title("💼 Multi-Platform Job Search Generator")
st.caption("Generate optimized search strings for LinkedIn Recruiter & DevelopmentAid")

# ---------- INITIALIZE SESSION STATE ----------
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

if 'domain_detected' not in st.session_state:
    st.session_state.domain_detected = None

# ---------- API CONFIG ----------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY", None)

if not api_key and "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]

if not api_key:
    st.error("❌ No API key found. Please set OPENAI_API_KEY in Streamlit Secrets or a .env file.")
else:
    st.success("🔐 API key loaded securely.")

model = st.selectbox("🧠 Choose Model", ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])

# ---------- JOB DESCRIPTION INPUT ----------
uploaded_file = st.file_uploader("📄 Upload Job Description", type=["txt", "pdf", "docx"])
job_description = st.text_area("Or paste job description text", height=250)

if uploaded_file and not job_description.strip():
    job_description = extract_text_from_file(uploaded_file)

# ---------- OPTIONS ----------
st.divider()
st.subheader("⚙️ Platform & Search Options")

col1, col2 = st.columns(2)
with col1:
    platform = st.selectbox("Target Platform", ["both", "linkedin", "developmentaid"])
with col2:
    domain = st.selectbox("Industry/Domain", ["auto_detect", "software_engineering", "international_development", "finance", "healthcare", "consulting", "general"])

col1, col2, col3 = st.columns(3)
include_location = col1.checkbox("Include location terms", True)
include_seniority = col2.checkbox("Include seniority levels", True)
include_variations = col3.checkbox("Generate search variations", True)


# ---------- VALIDATION FUNCTIONS ----------

def validate_linkedin_search(search_string: str) -> dict:
    """Validate LinkedIn Boolean search syntax"""
    issues = []
    warnings = []
    
    # Check for lowercase boolean operators
    if re.search(r'\b(and|or|not)\b', search_string):
        issues.append("Boolean operators must be UPPERCASE (AND, OR, NOT)")
    
    # Check quote pairing
    if search_string.count('"') % 2 != 0:
        issues.append("Unmatched quotes detected")
    
    # Check parentheses balance
    if search_string.count('(') != search_string.count(')'):
        issues.append("Unmatched parentheses")
    
    # Check length
    if len(search_string) > 1000:
        warnings.append("Search string very long (>1000 chars) - may be slow")
    
    # Count complexity
    and_count = search_string.upper().count(' AND ')
    or_count = search_string.upper().count(' OR ')
    title_count = search_string.lower().count('title:')
    
    # Complexity scoring
    complexity_score = (and_count * 2) + (or_count * 0.5) + (title_count * 3)
    
    if and_count > 4:
        warnings.append(f"Too many AND operators ({and_count}) - may be too restrictive")
    
    if title_count > 2:
        warnings.append(f"Multiple title: operators ({title_count}) - very restrictive")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "complexity_score": round(complexity_score, 1),
        "and_count": and_count,
        "or_count": or_count,
        "title_count": title_count,
        "length": len(search_string)
    }


def estimate_linkedin_results(search_string: str) -> dict:
    """Estimate LinkedIn result count based on complexity"""
    validation = validate_linkedin_search(search_string)
    
    # Scoring system
    score = 100  # Start at baseline
    
    # Each AND dramatically reduces results
    score *= (0.35 ** validation['and_count'])
    
    # Title operator is very restrictive
    score *= (0.25 ** validation['title_count'])
    
    # Length penalty
    if validation['length'] > 500:
        score *= 0.7
    
    # Estimate range
    if score > 50:
        estimate = "500-2000+"
        quality = "✅ Good breadth"
    elif score > 20:
        estimate = "100-500"
        quality = "✅ Acceptable"
    elif score > 5:
        estimate = "20-100"
        quality = "⚠️ May be restrictive"
    else:
        estimate = "0-20"
        quality = "❌ Likely too restrictive"
    
    return {
        "estimated_range": estimate,
        "score": round(score, 1),
        "quality": quality
    }


def validate_developmentaid_search(search_string: str) -> dict:
    """Validate DevelopmentAid search syntax"""
    issues = []
    warnings = []
    
    # Check for LinkedIn-style operators
    if re.search(r'\b(AND|OR|NOT)\b', search_string):
        warnings.append("Using uppercase AND/OR/NOT - DevelopmentAid uses +, |, - instead")
    
    # Check quote pairing
    if search_string.count('"') % 2 != 0:
        issues.append("Unmatched quotes detected")
    
    # Check parentheses balance
    if search_string.count('(') != search_string.count(')'):
        issues.append("Unmatched parentheses")
    
    # Check for boost operator usage
    if '^' in search_string and '|' not in search_string:
        warnings.append("Boost operator ^ should be used with OR (|)")
    
    # Check for invalid wildcard usage
    if re.search(r'\*\w+', search_string):
        issues.append("Wildcard * cannot be used before word stem (e.g., *finance is invalid)")
    
    if re.search(r'"[^"]*\*[^"]*"', search_string):
        issues.append("Wildcard * cannot be used inside quoted phrases")
    
    # Count operators
    and_count = search_string.count('+') + search_string.count(' AND ')
    or_count = search_string.count('|') + search_string.count(' OR ')
    not_count = search_string.count('-') + search_string.count(' NOT ')
    
    complexity_score = (and_count * 1.5) + (or_count * 0.3) + (not_count * 1)
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "complexity_score": round(complexity_score, 1),
        "and_count": and_count,
        "or_count": or_count,
        "not_count": not_count,
        "length": len(search_string)
    }


# ---------- DOMAIN CONTEXT ----------

def get_domain_context(domain: str) -> str:
    """Get domain-specific search context and examples"""
    
    contexts = {
        "software_engineering": """
## Software Engineering Context:

**Profile Language Patterns:**
- People say: "built", "developed", "implemented", "worked with"
- NOT: "proficiency in", "expertise in"
- Tools trump abstractions: "React" > "frontend framework"
- Action verbs matter: "deployed ML models" > "machine learning skills"

**Key Evidence Terms:**
- Languages: Python, JavaScript, Java, Go, Rust, C++
- Frameworks: React, Django, Flask, Node.js, Spring
- Cloud: AWS, Azure, GCP, EC2, Lambda, S3
- Tools: Docker, Kubernetes, Jenkins, Git, CI/CD

**Common Title Variations:**
- Software Engineer = Developer = SWE = Programmer
- Backend = Server-side = API Developer
- Full Stack = Full-stack = Fullstack
- DevOps = SRE = Platform Engineer

**Synonym Examples:**
"Machine Learning" → ML, AI, Data Science, "built models", "trained algorithms", TensorFlow, PyTorch
"Cloud" → AWS, Azure, GCP, "cloud infrastructure", "deployed to cloud", Docker, Kubernetes
""",
        
        "international_development": """
## International Development Context:

**Profile Language Patterns:**
- People say: "implemented project", "managed programme", "worked in"
- NOT: "project implementation expertise", "programme management proficiency"
- Donor names are critical: USAID, World Bank, UNDP, EU, DFID
- Geography matters: "East Africa", "field-based", "fragile states"

**Key Evidence Terms:**
- Sectors: WASH, M&E, MEAL, DRR, GBV, livelihoods, governance
- Donors: USAID, World Bank, UNDP, EU, DFID, AfDB, ADB
- Terms: capacity building, theory of change, logframe, field-based
- Locations: East Africa, West Africa, Sahel, MENA, South Asia

**Common Title Variations:**
- Project Manager = Programme Manager = PM = Project Coordinator
- M&E Specialist = MEAL Officer = Monitoring Officer
- WASH Specialist = Water Engineer = WASH Coordinator
- Team Leader = Chief of Party = Programme Director

**Synonym Examples:**
"M&E" → Monitoring and Evaluation, MEAL, "tracked indicators", "evaluated programs", logframe
"WASH" → Water Sanitation, "water projects", "sanitation programs", borehole, water supply
""",
        
        "finance": """
## Finance Context:

**Profile Language Patterns:**
- People say: "analyzed", "modeled", "managed portfolio", "closed deals"
- NOT: "financial analysis expertise", "portfolio management skills"
- Certifications matter: CFA, FRM, CPA, Series 7
- Deal experience is concrete: "M&A transaction", "IPO", "$500M AUM"

**Key Evidence Terms:**
- Skills: financial modeling, valuation, DCF, LBO, due diligence
- Tools: Bloomberg, FactSet, Excel, Python, R
- Products: equity, fixed income, derivatives, structured products
- Regulations: Basel, Dodd-Frank, MiFID, SOX

**Common Title Variations:**
- Financial Analyst = Finance Analyst = Investment Analyst
- Portfolio Manager = Fund Manager = Asset Manager
- Investment Banking = IB = M&A Analyst

**Synonym Examples:**
"Financial Modeling" → DCF, valuation, "built models", Excel, "financial analysis"
"Risk Management" → "risk analysis", VaR, "stress testing", "risk assessment"
"""
    }
    
    return contexts.get(domain, "")


# ---------- IMPROVED PROMPT ----------

def create_improved_prompt(job_text: str, platform: str, domain: str) -> str:
    """
    Create context-aware prompt for better search string generation
    """
    
    domain_context = get_domain_context(domain) if domain != "auto_detect" else ""
    
    prompt = f"""You are an expert recruiter who creates EFFECTIVE search strings that actually return results.

# CRITICAL PHILOSOPHY: SIMPLER IS BETTER

The biggest mistake in Boolean search is over-engineering. Each restriction cuts results by 50-80%.

## LinkedIn Reality Check:
- Each AND operator = 50-70% reduction in results
- title: operator = 80% reduction in results  
- Exact phrases = 40% reduction in results
- Perfect match search with 5 ANDs = 0-20 results ❌
- Simple search with 2 ANDs = 200-500 results ✅

## DevelopmentAid Reality Check:
- Focus on sector keywords and donor experience
- Use boost operator (^) to prioritize key terms
- Include geographic context
- Broader searches work better than narrow ones

# PLATFORM SYNTAX:

## LinkedIn Recruiter:
- AND, OR, NOT (must be UPPERCASE)
- Quotes for exact phrases: "Machine Learning"
- Parentheses for grouping: (Python OR Java)
- title: operator (use sparingly!)
- Maximum 3 AND operators in primary search
- Maximum 5 AND operators even in focused search

## DevelopmentAid:
- AND: `+` or space (space is assumed AND)
- OR: `|` or comma `,`
- NOT: `-` (minus)
- Exact phrase: `"water sanitation"`
- Grouping: `(water|sanitation) + (project|programme)`
- Wildcard: `financ*` (finds finance, financial, financing)
- Boost: `term^5` (must use with OR: `(water)^10 | sanitation`)
- Example: `(WASH|"water sanitation")^10 | (M&E)^8 + (USAID|"World Bank")`

# YOUR TASK:

Analyze the job description and create SIMPLE, EFFECTIVE searches.

{domain_context}

## Step 1: Extract Core Requirements

Identify:
1. **2-3 Core Skills** (absolute must-haves that define the role)
2. **3-5 Secondary Skills** (nice-to-haves for filtering)
3. **5-10 Job Title Variations** (be creative!)
4. **Evidence Terms** (tools/outputs that prove skills)

## Step 2: Generate Context-Aware Synonyms

For each core skill, provide:
- **Formal terms**: Professional/academic language
- **Profile phrases**: How people actually describe doing this work
- **Evidence terms**: Tools, outputs, certifications that prove it

Example:
Requirement: "Machine Learning"
- Formal: "Machine Learning", "ML", "Artificial Intelligence", "Data Science"
- Profile: "built ML models", "trained algorithms", "deployed models", "worked on AI"
- Evidence: "TensorFlow", "PyTorch", "scikit-learn", "model deployment"

## Step 3: Create Tiered Searches

Generate 4 search tiers:

1. **broad** (300-1000 results): 1-2 core concepts, mostly OR variations
2. **primary** (100-500 results): Add one critical filter
3. **focused** (50-200 results): Add niche requirements  
4. **ultra_specific** (10-50 results): Kitchen sink for perfect matches

## Search Building Formula:

**LinkedIn:**
```
Broad: (skill1 OR skill2 OR skill3)
Primary: (skill1 OR skill2 OR skill3) AND (role1 OR role2 OR role3)
Focused: (skill1 OR skill2 OR skill3) AND (role1 OR role2 OR role3) AND (evidence1 OR evidence2)
Ultra_specific: Add location, seniority, or more evidence
```

**DevelopmentAid:**
```
Broad: (sector1|sector2)^10 | (sector3)^8
Primary: (sector1|sector2)^10 | (sector3) + (donor1|donor2)
Focused: (sector1|sector2)^10 + (donor1|donor2) + (geography1|geography2)
Ultra_specific: Add specific technical skills or certifications
```

# CONFIGURATION:
- Platform: {platform}
- Domain: {domain}
- Include location: {include_location}
- Include seniority: {include_seniority}

# JOB DESCRIPTION:
{job_text[:15000]}

# OUTPUT FORMAT (JSON):

{{
  "domain_detected": "Detected domain/industry",
  
  "analysis": {{
    "coreSkills": ["2-3 absolute must-haves"],
    "secondarySkills": ["3-5 nice-to-haves"],
    "jobTitles": ["5-10 title variations"],
    "seniorityLevel": "entry|mid|senior|lead",
    "keyEvidence": ["Tools/outputs that prove skills"]
  }},
  
  "contextualSynonyms": {{
    "SkillName": {{
      "formal": ["Professional terms"],
      "profile_language": ["How people describe doing it"],
      "evidence": ["Tools/outputs"],
      "combined_or_clause": "(term1 OR term2 OR term3 OR tool1 OR tool2)"
    }}
  }},
  
  "linkedinSearches": {{
    "broad": {{
      "search": "Search string with 1-2 AND operators max",
      "rationale": "Why this structure",
      "estimated_results": "300-1000"
    }},
    "primary": {{
      "search": "Search string with 2-3 AND operators max",
      "rationale": "Why this structure", 
      "estimated_results": "100-500"
    }},
    "focused": {{
      "search": "Search string with 3-4 AND operators max",
      "rationale": "Why this structure",
      "estimated_results": "50-200"
    }},
    "ultra_specific": {{
      "search": "Kitchen sink search",
      "rationale": "For perfect matches only",
      "estimated_results": "10-50"
    }}
  }},
  
  "developmentaidSearches": {{
    "broad": {{
      "search": "Simple sector search with boost",
      "rationale": "Why this structure",
      "estimated_results": "200-800"
    }},
    "primary": {{
      "search": "Sector + donor/geography",
      "rationale": "Why this structure",
      "estimated_results": "80-300"
    }},
    "focused": {{
      "search": "Sector + donor + specific skills",
      "rationale": "Why this structure",
      "estimated_results": "30-150"
    }},
    "ultra_specific": {{
      "search": "All criteria with wildcards",
      "rationale": "For exact matches",
      "estimated_results": "10-50"
    }}
  }},
  
  "searchStrategy": "2-3 sentences explaining the overall approach",
  "warnings": ["Any concerns about search difficulty"],
  "manualReviewTips": ["What to look for when reviewing results"]
}}

# QUALITY CHECKLIST:

LinkedIn:
✓ Maximum 3 AND operators in primary search
✓ Each OR group has 3-5 variations
✓ Includes both formal terms and profile language
✓ Evidence terms (tools) included
✓ Avoid or minimize title: operator usage

DevelopmentAid:
✓ Uses correct syntax: +, |, -, not AND/OR/NOT
✓ Boost operator (^) used with key terms
✓ Includes sector-specific terminology
✓ Includes donor/geography context
✓ Wildcard (*) used for term variations

Generate searches that WILL RETURN RESULTS, not perfect theoretical matches!"""

    return prompt


# ---------- ANALYZE FUNCTION ----------

def analyze_job_description(job_text: str, platform: str, domain: str):
    """Analyze job description and generate platform-specific searches"""
    
    if not api_key:
        st.error("Please provide an OpenAI API key")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = create_improved_prompt(job_text, platform, domain)
        
        with st.spinner("🧠 Analyzing job description and generating optimized searches..."):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert recruiter specializing in creating effective Boolean search strings. You understand the critical importance of simple searches that return results."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
        
        content = response.choices[0].message.content
        
        try:
            result = json.loads(content)
            st.session_state.analysis_results = result
            st.session_state.domain_detected = result.get("domain_detected", domain)
            return result
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(content[start:end+1])
                st.session_state.analysis_results = result
                st.session_state.domain_detected = result.get("domain_detected", domain)
                return result
            else:
                st.error("⚠️ Failed to parse JSON from AI response.")
                with st.expander("See raw response"):
                    st.code(content)
                return None
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


# ---------- GENERATE BUTTON ----------

if st.button("🔍 Generate Optimized Search Strings", type="primary"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    elif not job_description.strip():
        st.error("Please upload or paste a job description.")
    else:
        # Detect domain if auto
        detected_domain = domain if domain != "auto_detect" else "general"
        
        # Generate analysis
        analysis = analyze_job_description(job_description, platform, detected_domain)


# ---------- DISPLAY RESULTS ----------

if st.session_state.analysis_results:
    analysis = st.session_state.analysis_results
    
    st.success("✅ Analysis complete!")
    
    # Clear button
    if st.button("🗑️ Clear Results & Start New Search"):
        st.session_state.analysis_results = None
        st.session_state.domain_detected = None
        st.rerun()
    
    # Show domain detection
    if st.session_state.domain_detected:
        st.info(f"🎯 **Detected Domain:** {st.session_state.domain_detected}")
    
    # Show strategy
    if analysis.get("searchStrategy"):
        st.markdown("### 📋 Search Strategy")
        st.write(analysis["searchStrategy"])
    
    st.markdown("---")
    
    # Show core analysis
    with st.expander("🔍 Job Analysis", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Core Requirements")
            for skill in analysis.get("analysis", {}).get("coreSkills", []):
                st.markdown(f"🎯 **{skill}**")
            
            st.subheader("Job Title Variations")
            for title in analysis.get("analysis", {}).get("jobTitles", []):
                st.markdown(f"- {title}")
        
        with col2:
            st.subheader("Secondary Skills")
            for skill in analysis.get("analysis", {}).get("secondarySkills", []):
                st.markdown(f"- {skill}")
            
            st.subheader("Key Evidence Terms")
            for evidence in analysis.get("analysis", {}).get("keyEvidence", []):
                st.markdown(f"- {evidence}")
    
    # Show contextual synonyms
    if "contextualSynonyms" in analysis:
        with st.expander("🔤 Contextual Synonym Mapping", expanded=False):
            for skill, synonyms in analysis["contextualSynonyms"].items():
                st.markdown(f"### {skill}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Formal Terms:**")
                    for term in synonyms.get("formal", []):
                        st.markdown(f"- {term}")
                
                with col2:
                    st.markdown("**Profile Language:**")
                    for phrase in synonyms.get("profile_language", []):
                        st.markdown(f"- {phrase}")
                
                with col3:
                    st.markdown("**Evidence:**")
                    for evidence in synonyms.get("evidence", []):
                        st.markdown(f"- {evidence}")
                
                if synonyms.get("combined_or_clause"):
                    st.code(synonyms["combined_or_clause"], language="text")
                
                st.markdown("---")
    
    st.markdown("---")
    
    # LinkedIn searches
    if "linkedinSearches" in analysis and platform in ["both", "linkedin"]:
        st.header("🔗 LinkedIn Recruiter Search Strings")
        
        searches = analysis["linkedinSearches"]
        
        for key, search_data in searches.items():
            # Handle both dict and string formats
            if isinstance(search_data, dict):
                search_string = search_data.get("search", "")
                rationale = search_data.get("rationale", "")
                estimated = search_data.get("estimated_results", "")
            else:
                search_string = search_data
                rationale = ""
                estimated = ""
            
            st.subheader(f"LinkedIn - {key.replace('_', ' ').title()}")
            
            # Validate and estimate
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.expander("Click to view and copy", expanded=True):
                    st.code(search_string, language="text")
                    
                    if rationale:
                        st.caption(f"**Rationale:** {rationale}")
            
            with col2:
                # Validation
                validation = validate_linkedin_search(search_string)
                
                if validation["valid"]:
                    st.success("✅ Valid")
                else:
                    st.error("❌ Issues")
                    for issue in validation["issues"]:
                        st.warning(f"⚠️ {issue}")
                
                # Warnings
                for warning in validation.get("warnings", []):
                    st.warning(f"⚠️ {warning}")
                
                # Estimation
                estimate = estimate_linkedin_results(search_string)
                st.metric("Est. Results", estimate["estimated_range"])
                st.caption(estimate["quality"])
                
                # Stats
                st.caption(f"AND: {validation['and_count']}")
                st.caption(f"OR: {validation['or_count']}")
                st.caption(f"Length: {validation['length']}")
                
                # Direct search link
                import urllib.parse
                encoded_query = urllib.parse.quote(search_string)
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"
                st.markdown(f"[🔍 Search Now]({search_url})")
            
            st.markdown("---")
    
    # DevelopmentAid searches
    if "developmentaidSearches" in analysis and platform in ["both", "developmentaid"]:
        st.header("🌱 DevelopmentAid Search Strings")
        
        st.info("""
        **DevelopmentAid Syntax Guide:**
        - `+` or space = AND
        - `|` or `,` = OR
        - `-` = NOT
        - `"phrase"` = exact phrase
        - `term*` = wildcard (finds term, terms, terminal, etc.)
        - `(term)^10` = boost operator (use with OR)
        """)
        
        searches = analysis["developmentaidSearches"]
        
        for key, search_data in searches.items():
            # Handle both dict and string formats
            if isinstance(search_data, dict):
                search_string = search_data.get("search", "")
                rationale = search_data.get("rationale", "")
                estimated = search_data.get("estimated_results", "")
            else:
                search_string = search_data
                rationale = ""
                estimated = ""
            
            st.subheader(f"DevelopmentAid - {key.replace('_', ' ').title()}")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                with st.expander("Click to view and copy", expanded=True):
                    st.code(search_string, language="text")
                    
                    if rationale:
                        st.caption(f"**Rationale:** {rationale}")
            
            with col2:
                # Validation
                validation = validate_developmentaid_search(search_string)
                
                if validation["valid"]:
                    st.success("✅ Valid")
                else:
                    st.error("❌ Issues")
                    for issue in validation["issues"]:
                        st.warning(f"⚠️ {issue}")
                
                # Warnings
                for warning in validation.get("warnings", []):
                    st.warning(f"⚠️ {warning}")
                
                # Stats
                st.caption(f"AND (+): {validation['and_count']}")
                st.caption(f"OR (|): {validation['or_count']}")
                st.caption(f"NOT (-): {validation['not_count']}")
                
                if estimated:
                    st.metric("Est. Results", estimated)
                
                # Direct search link
                import urllib.parse
                encoded_query = urllib.parse.quote(search_string)
                search_url = f"https://www.developmentaid.org/search?q={encoded_query}"
                st.markdown(f"[🔍 Search Now]({search_url})")
            
            st.markdown("---")
    
    # Tips and warnings
    if analysis.get("warnings") or analysis.get("manualReviewTips"):
        st.markdown("---")
        
        if analysis.get("warnings"):
            st.subheader("⚠️ Warnings")
            for warning in analysis["warnings"]:
                st.warning(warning)
        
        if analysis.get("manualReviewTips"):
            st.subheader("💡 Manual Review Tips")
            for tip in analysis["manualReviewTips"]:
                st.markdown(f"- {tip}")
    
    # Export options
    st.markdown("---")
    st.subheader("📥 Export Search Strings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_str = json.dumps(analysis, indent=2)
        st.download_button(
            label="📄 Download as JSON",
            data=json_str,
            file_name="search_strings.json",
            mime="application/json"
        )
    
    with col2:
        # Text export
        text_output = f"""# Job Search Strings Generated

## Strategy
{analysis.get('searchStrategy', '')}

## Domain: {st.session_state.domain_detected or 'General'}

"""
        
        if "linkedinSearches" in analysis:
            text_output += "\n## LinkedIn Recruiter Searches\n\n"
            for key, search_data in analysis["linkedinSearches"].items():
                search = search_data.get("search", search_data) if isinstance(search_data, dict) else search_data
                text_output += f"### {key.replace('_', ' ').title()}\n{search}\n\n"
        
        if "developmentaidSearches" in analysis:
            text_output += "\n## DevelopmentAid Searches\n\n"
            for key, search_data in analysis["developmentaidSearches"].items():
                search = search_data.get("search", search_data) if isinstance(search_data, dict) else search_data
                text_output += f"### {key.replace('_', ' ').title()}\n{search}\n\n"
        
        if analysis.get("manualReviewTips"):
            text_output += "\n## Manual Review Tips\n"
            for tip in analysis["manualReviewTips"]:
                text_output += f"- {tip}\n"
        
        st.download_button(
            label="📄 Download as Text",
            data=text_output,
            file_name="search_strings.txt",
            mime="text/plain"
        )

# ---------- FOOTER ----------
st.markdown("---")
st.caption("💡 **Pro Tip:** Start with 'broad' searches to gauge the candidate pool, then narrow down with 'primary' or 'focused' searches.")
