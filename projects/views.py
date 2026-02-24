
import json

from dotenv import load_dotenv
import os

from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field, ValidationError
from typing import List
from langchain_core.output_parsers import PydanticOutputParser
from langchain_ollama import ChatOllama
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import Project
import logging
from django_ratelimit.decorators import ratelimit
from django.utils import timezone
from langchain_community.tools import DuckDuckGoSearchRun
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy


load_dotenv()
logger = logging.getLogger(__name__)
repl = PythonREPL()

class BOQItem(BaseModel):
    item: str = Field(..., description="Name of the item")
    quantity: float = Field(..., description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    unit_rate_naira: float = Field(..., description="Rate per unit in Naira")
    total_naira: float = Field(..., description="Total cost in Naira")

class BOQOutput(BaseModel):
    items: List[BOQItem]
    grand_total_naira: float
    contingency_percent: float = Field(..., ge=5, le=30)
    risks: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)

class ProjectCreateView(CreateView):
    model = Project
    fields = ['name', 'description']
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:my_projects')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

parser = PydanticOutputParser(pydantic_object=BOQOutput)

@ratelimit(key='user', rate='5/m', method='POST', block=True)
@require_POST
@login_required
def analyze_boq(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)

    if not project.description.strip():
        return JsonResponse({"success": False, "error": "Project description is empty"}, status=400)

    llm = ChatOllama(
        model="llama3.1:8b",
        temperature=0.2,
        max_tokens=1200,
        timeout=120
    )

    # ── Fetch real prices FIRST ───────────────────────────────────────────────
    search = DuckDuckGoSearchRun()
    materials = ["12mm rebar", "cement 50kg bag", "ready mix concrete m3"]
    price_info = ""
    for mat in materials:
        try:
            query = f"current price {mat} Lagos Nigeria Naira"
            result = search.run(query)
            price_info += f"{mat}: {result}\n"
        except Exception as e:
            logger.warning(f"Price lookup failed for {mat}: {e}")
            price_info += f"{mat}: lookup failed\n"

    # ── Build prompt with prices ──────────────────────────────────────────────
    base_prompt = f"""You are a senior Quantity Surveyor in Lagos 2026.
Project description: {project.description}

Use these current prices (approximate):
{price_info}

This is a small element — do NOT assume a full building.
For example, a 3m beam has concrete volume ~0.3-0.5 m³, rebar ~5-20 kg.

Generate realistic BOQ summary.
Return **ONLY** valid JSON matching this schema. No other text, no explanations, no markdown, no code blocks.
{parser.get_format_instructions()}

Use correct quantities for the described scale.
Calculate totals correctly (quantity × rate)."""

    raw_output = ""
    try:
        response = llm.invoke(base_prompt)
        raw_output = response.content.strip()
        logger.debug(f"Raw LLM output: {raw_output[:500]}...")
        parsed = parser.parse(raw_output)

        # Validate totals with code execution
        try:
            validation_code = "\n".join(
                f"item_{i}_total = {item.quantity} * {item.unit_rate_naira}"
                for i, item in enumerate(parsed.items)
            ) + "\n" + "grand = " + " + ".join(f"item_{i}_total" for i in range(len(parsed.items)))
            validated_grand = float(repl.run(validation_code + "\ngrand"))
            if abs(validated_grand - parsed.grand_total_naira) > parsed.grand_total_naira * 0.05:
                logger.warning("Total mismatch detected")
        except Exception as math_e:
            logger.warning(f"Math validation failed: {math_e}")

        # Save to DB
        project.boq_result = parsed.model_dump()
        project.boq_generated_at = timezone.now()
        project.save(update_fields=['boq_result', 'boq_generated_at'])

    except (ValidationError, json.JSONDecodeError) as e1:
        logger.error(f"Parse failed (attempt 1): {e1} | Raw: {raw_output}")
        retry_prompt = f"{base_prompt}\n\nPrevious failed. Return ONLY valid JSON. No intro text, no markdown fences."
        try:
            response = llm.invoke(retry_prompt)
            raw_output = response.content.strip()
            logger.debug(f"Raw retry: {raw_output[:500]}...")
            parsed = parser.parse(raw_output)
            project.boq_result = parsed.model_dump()
            project.boq_generated_at = timezone.now()
            project.save(update_fields=['boq_result', 'boq_generated_at'])
        except Exception as e2:
            logger.error(f"Retry failed: {e2} | Raw: {raw_output}")
            return JsonResponse({
                "success": False,
                "error": f"Parsing failed twice. Raw output for debugging: {raw_output}\nError: {str(e2)}"
            }, status=500)

    return JsonResponse({
        "success": True,
        "boq": parsed.model_dump(),
        "raw": raw_output  # for debugging — remove in prod
    })



@login_required
def my_projects(request):
    all_projects = Project.objects.all()
    my_projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'projects/my_projects.html', {
        'projects': my_projects,
        'all_projects_count': all_projects.count(),
        'my_projects_count': my_projects.count(),
        'current_user': request.user.username,
    })

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    return render(request, 'projects/project_detail.html', {'project': project})

# search = DuckDuckGoSearchRun()

# def get_price(material: str) -> str:
#     query = f"current price {material} Lagos Nigeria Naira 2026"
#     return search.run(query)

# def validate_totals(items):
#     code = "\n".join([f"total_{i} = {item['quantity']} * {item['unit_rate_naira']}" for i, item in enumerate(items)]) + "\n" + "grand = " + " + ".join([f"total_{i}" for i in range(len(items))])
#     return repl.run(code)