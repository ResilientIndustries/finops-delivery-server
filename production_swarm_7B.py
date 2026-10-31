import os
import sys
import subprocess
from typing import Dict, TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from github import Github
import stripe
import resend

# =====================================================================
# 1. HARDWARE-OPTIMIZED CONFIGURATION (RTX 5060 - 8GB VRAM SAFE)
# =====================================================================
# Swapping to 7B ensures 100% GPU VRAM offloading with zero System RAM thrashing
coder_llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0.2)
scout_llm = ChatOllama(model="llama3.1:8b", temperature=0.7)

STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")
RESEND_KEY = os.getenv("RESEND_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TARGET_EMAIL = os.getenv("NOTIFICATION_EMAIL")

class EngineState(TypedDict):
    discovered_trend: str
    sales_copy: str
    digital_product_md: str
    stripe_link: str
    github_repo_url: str
    qa_passed: bool
    approved_by_human: bool

# =====================================================================
# 2. AGENT NODE IMPLEMENTATIONS
# =====================================================================
def trend_scout_node(state: EngineState) -> Dict:
    print("\n🔍 [Agent 1: Scout] Searching dynamic B2B Cloud FinOps friction points...")
    
    prompt = """
    Identify ONE specific, high-cost cloud infrastructure inefficiency currently facing DevOps teams (e.g., in AWS, Kubernetes, GCP, or Snowflake).
    Output ONLY a concise title of the problem (max 10 words). No introductory text or quotes.
    """
    response = scout_llm.invoke(prompt)
    state["discovered_trend"] = response.content.strip().replace('"', '')
    print(f"-> Dynamic Niche Identified: {state['discovered_trend']}")
    return state

def product_architect_node(state: EngineState) -> Dict:
    print("\n💻 [Agent 2: Architect] Generating production-grade FinOps Blueprint (Qwen 7B GPU)...")
    prompt = f"""
    [ROLE] Senior Staff Cloud Infrastructure Architect.
    [TASK] Write a dense, production-ready Markdown implementation blueprint for: "{state['discovered_trend']}".
    Must include:
    1. Executive Summary & Problem Diagnosis
    2. Concrete Code/YAML/Terraform Configuration Block
    3. Step-by-step rollout commands.
    No introductory fluff.
    """
    state["digital_product_md"] = coder_llm.invoke(prompt).content
    
    copy_prompt = f"Write crisp, high-converting direct-response sales copy targeting a DevOps lead for this product:\n{state['digital_product_md'][:300]}"
    state["sales_copy"] = scout_llm.invoke(copy_prompt).content
    return state

def qa_validator_node(state: EngineState) -> Dict:
    print("\n🧪 [Agent 3: QA] Validating output & writing blueprint locally...")
    
    # Save output to a local Markdown file
    output_filename = "generated_blueprint.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"# {state['discovered_trend']}\n\n")
        f.write(state["digital_product_md"])
    
    print(f"💾 Full blueprint saved locally to: `{output_filename}`")
    
    # Basic quality verification check
    state["qa_passed"] = len(state["digital_product_md"]) > 200
    return state

def human_gate_node(state: EngineState) -> Dict:
    print("\n" + "="*50)
    print("💰 [HUMAN GATE] REVIEW ASSET BEFORE STRIKE & GITHUB DEPLOYMENT")
    print("="*50)
    print(f"Niche: {state['discovered_trend']}")
    print("\n--- PRODUCT PREVIEW ---")
    print(state["digital_product_md"][:350] + "\n[...]")
    print(f"\n💡 Note: You can open 'generated_blueprint.md' in your folder to inspect the full file.")
    
    decision = input("\nApprove live API deployment (Stripe + GitHub Repo)? (y/n): ")
    state["approved_by_human"] = (decision.lower() == 'y')
    return state

def cloud_deployment_node(state: EngineState) -> Dict:
    if not state["approved_by_human"]:
        print("\n🛑 Execution halted by operator. Skipping cloud deployment.")
        return state
        
    print("\n🚀 [Agent 4: Cloud Deployer] Provisioning Stripe & GitHub infrastructure...")
    
    # 1. Provision GitHub Private Vault
    if GITHUB_TOKEN:
        try:
            gh = Github(GITHUB_TOKEN)
            user = gh.get_user()
            repo_slug = "".join([c if c.isalnum() else "-" for c in state["discovered_trend"].lower()])[:40]
            repo_name = f"finops-{repo_slug}"
            try:
                repo = user.get_repo(repo_name)
            except:
                repo = user.create_repo(name=repo_name, description=f"FinOps Assets: {state['discovered_trend']}", private=True)
                repo.create_file(path="README.md", message="Initial commit by Swarm", content=state["digital_product_md"], branch="main")
            state["github_repo_url"] = repo.html_url
            print(f"-> Private GitHub Vault created: {state['github_repo_url']}")
        except Exception as e:
            state["github_repo_url"] = f"GitHub Error: {e}"
            print(f"-> {state['github_repo_url']}")
    else:
        print("-> GITHUB_TOKEN not set. Skipping Git vault provision.")

    # 2. Provision Stripe Checkout Session
    if STRIPE_KEY:
        try:
            stripe.api_key = STRIPE_KEY
            product = stripe.Product.create(name=f"Blueprint: {state['discovered_trend'][:40]}")
            price = stripe.Price.create(product=product.id, unit_amount=4900, currency="usd")
            session = stripe.checkout.Session.create(
                success_url="https://yourdomain.com",
                cancel_url="https://yourdomain.com",
                line_items=[{"price": price.id, "quantity": 1}],
                mode="payment",
            )
            state["stripe_link"] = session.url
            print(f"-> Stripe Checkout Link generated: {state['stripe_link']}")
        except Exception as e:
            state["stripe_link"] = f"Stripe Error: {e}"
            print(f"-> {state['stripe_link']}")
    else:
        print("-> STRIPE_SECRET_KEY not set. Skipping payment link generation.")

    # 3. Dispatch Notification via Resend
    if RESEND_KEY and TARGET_EMAIL:
        try:
            resend.api_key = RESEND_KEY
            resend.Emails.send({
                "from": "SwarmEngine <onboarding@resend.dev>",
                "to": TARGET_EMAIL,
                "subject": f"🔥 FINOPS LAUNCH: {state['discovered_trend'][:30]}",
                "html": f"<h2>Launch Ready</h2><p>Checkout: {state.get('stripe_link', 'N/A')}</p><p>Repo: {state.get('github_repo_url', 'N/A')}</p>"
            })
            print("-> Telemetry report emailed to operator.")
        except Exception as e:
            print(f"-> Email error: {e}")

    return state

# =====================================================================
# 3. GRAPH ORCHESTRATION ASSEMBLY
# =====================================================================
builder = StateGraph(EngineState)
builder.add_node("scout", trend_scout_node)
builder.add_node("architect", product_architect_node)
builder.add_node("qa", qa_validator_node)
builder.add_node("gate", human_gate_node)
builder.add_node("deployer", cloud_deployment_node)

builder.set_entry_point("scout")
builder.add_edge("scout", "architect")
builder.add_edge("architect", "qa")
builder.add_edge("qa", "gate")
builder.add_edge("gate", "deployer")
builder.add_edge("deployer", END)

app = builder.compile()

if __name__ == "__main__":
    initial_state = {
        "discovered_trend": "",
        "sales_copy": "",
        "digital_product_md": "",
        "stripe_link": "",
        "github_repo_url": "",
        "qa_passed": False,
        "approved_by_human": False
    }
    app.invoke(initial_state)