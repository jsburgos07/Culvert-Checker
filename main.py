"""
Culvert & Drainage Pipe Size Checker
Educational screening tool using the Rational Method
and Manning's equation. Not a substitute for an engineer.
"""
from drafter import *
from dataclasses import dataclass
from math import pi

SURFACE_C= {"Pavement/roof": 0.90, "Gravel": 0.60,"Residential yard": 0.35,"Lawn/grass": 0.20,"Forest/woods": 0.15}

MATERIAL_N= {"Concrete": 0.013,"Corrugated metal": 0.024,"PVC/smooth HDPE": 0.010}

STANDARD_SIZES= [12, 15, 18, 24, 30, 36, 42, 48, 60, 72]

ALLOWED_PERCENT_FULL= 80.0  #design to 80% of capacity
MIN_VELOCITY= 2.0   #ft/s, below this sediment can build up
MAX_VELOCITY= 10.0  #ft/s, above this erosion is a risk

@dataclass
class State:
    error: str
    area: float
    surface: str
    c_value: float
    intensity: float
    diameter: float
    slope_percent: float
    material: str
    design_flow: float
    capacity: float
    velocity: float
    percent_used: float
    verdict: str
    warnings: list[str]
    recommended: int


def new_state()->State:
    return State("", 0.0, "Pavement/roof", 0.9, 0.0, 0.0, 0.0,"Concrete", 0.0, 0.0, 0.0, 0.0, "", [], 0)

def to_positive_number(text: str)->float:
    #Convert text to a positive float, or return -1.0 if invalid
    try:
        value = float(text.strip())
    except ValueError:
        return -1.0
    if value <= 0:
        return -1.0
    return value


def calc_design_flow(c: float, intensity: float, area: float)->float:
    #Rational Method (Q = C * i * A)
    return c * intensity * area


def calc_area_full(diameter_in: float)->float:
    #Horizontal area of a full circular pipe (sq ft)
    d_ft = diameter_in/12
    return pi * d_ft **2/4


def calc_hydraulic_radius(diameter_in: float)->float:
    #Hydraulic radius of a full circular pipe (ft) = D / 4
    return (diameter_in/12)/4


def calc_capacity(diameter_in: float, slope_percent: float, n: float)->float:
    #Manning's equation, full flow (cfs)
    area= calc_area_full(diameter_in)
    radius = calc_hydraulic_radius(diameter_in)
    slope=slope_percent / 100
    return (1.49 / n) * area * radius ** (2 / 3) * slope ** 0.5


def calc_velocity(capacity: float, diameter_in: float)->float:
    #Full-flow velocity (ft/s) = Q / A
    return capacity/calc_area_full(diameter_in)


def build_warnings(velocity: float)->list[str]:
    notes = []
    if velocity<MIN_VELOCITY:
        notes.append("Velocity is low (under 2 ft/s). Sediment may build up in the pipe.")
    if velocity>MAX_VELOCITY:
        notes.append("Velocity is high (over 10 ft/s). Erosion at the outlet is a risk.")
    return notes


def find_recommended_size(design_flow: float, slope_percent: float, n: float)->int:
    #Smallest diameter that handles the flow or 0 if none do
    for size in STANDARD_SIZES:
        cap = calc_capacity(size, slope_percent, n)
        if design_flow <=cap * (ALLOWED_PERCENT_FULL/100):
            return size
    return 0


#pages
@route
def index(state: State)->Page:
    return Page(state, [
        Header("Culvert & Drainage Pipe Size Checker"),
        "Find out whether a drainage pipe or culvert is big enough for the "
        "water that flows to it during a design storm.",
        HorizontalRule(),
        "You will enter details about the area draining to the pipe, then "
        "details about the pipe. The tool calculates the flow the pipe must "
        "carry and compares it to what the pipe can carry.",
        LineBreak(),
        ("Disclaimer: "),
        "This is an educational estimate only. Real culvert design involves "
        "headwater, tailwater, inlet/outlet control, and local regulations. "
        "Always consult a licensed engineer.",
        Button("Start", watershed_page),
    ])


@route
def watershed_page(state: State) -> Page:
    content = [
        Header("Step 1: Drainage Area"),
        "Describe the land that drains to the pipe.",
    ]
    if state.error:
        content.append(Bold(state.error))
    content += [
        LineBreak(),
        "Drainage area (acres):",
        TextBox("area", str(state.area) if state.area > 0 else ""),
        LineBreak(),
        "Main surface type:",
        SelectBox("surface", list(SURFACE_C.keys()), state.surface),
        LineBreak(),
        "Design rainfall intensity (inches per hour). "
        "A 10-year storm is often around 3 to 6 in/hr for short durations:",
        TextBox("intensity", str(state.intensity) if state.intensity > 0 else ""),
        LineBreak(),
        Button("Next", save_watershed),
        Button("Back", index),
    ]
    return Page(state, content)


@route
def save_watershed(state: State, area: str, surface: str, intensity: str) -> Page:
    area_value = to_positive_number(area)
    intensity_value = to_positive_number(intensity)

    if area_value < 0:
        state.error = "Drainage area must be a number greater than 0."
        return watershed_page(state)
    if intensity_value < 0:
        state.error = "Rainfall intensity must be a number greater than 0."
        return watershed_page(state)

    state.error = ""
    state.area = area_value
    state.surface = surface
    state.c_value = SURFACE_C[surface]
    state.intensity = intensity_value
    return pipe_page(state)


@route
def pipe_page(state: State) -> Page:
    content = [
        Header("Step 2: Pipe Details"),
        "Describe the pipe you want to check.",
    ]
    if state.error:
        content.append(Bold(state.error))
    content += [
        LineBreak(),
        "Pipe diameter (inches):",
        TextBox("diameter", str(state.diameter) if state.diameter > 0 else ""),
        LineBreak(),
        "Pipe slope (percent, e.g. 1 means 1 foot of drop per 100 feet):",
        TextBox("slope", str(state.slope_percent) if state.slope_percent > 0 else ""),
        LineBreak(),
        "Pipe material:",
        SelectBox("material", list(MATERIAL_N.keys()), state.material),
        LineBreak(),
        Button("Check Pipe", calculate),
        Button("Back", watershed_page),
    ]
    return Page(state, content)


@route
def calculate(state: State, diameter: str, slope: str, material: str) -> Page:
    diameter_value = to_positive_number(diameter)
    slope_value = to_positive_number(slope)

    if diameter_value < 0:
        state.error = "Diameter must be a number greater than 0."
        return pipe_page(state)
    if slope_value < 0:
        state.error = "Slope must be a number greater than 0."
        return pipe_page(state)
    if slope_value > 100:
        state.error = "Slope looks too large. Enter a percent between 0 and 100."
        return pipe_page(state)

    state.error = ""
    state.diameter = diameter_value
    state.slope_percent = slope_value
    state.material = material
    n = MATERIAL_N[material]

    state.design_flow = calc_design_flow(state.c_value, state.intensity, state.area)
    state.capacity = calc_capacity(diameter_value, slope_value, n)
    state.velocity = calc_velocity(state.capacity, diameter_value)
    state.percent_used = state.design_flow / state.capacity * 100
    state.warnings = build_warnings(state.velocity)

    if state.percent_used <= ALLOWED_PERCENT_FULL:
        state.verdict = "ADEQUATE"
        state.recommended = 0
    else:
        state.verdict = "UNDERSIZED"
        state.recommended = find_recommended_size(state.design_flow, slope_value, n)

    return results_page(state)


@route
def results_page(state: State) -> Page:
    content = [
        Header("Results"),
        Header("Verdict: " + state.verdict, 2),
        HorizontalRule(),
        Bold("What you entered"),
        LineBreak(),
        "Drainage area: " + str(state.area) + " acres",
        LineBreak(),
        "Surface: " + state.surface + " (C = " + str(state.c_value) + ")",
        LineBreak(),
        "Rainfall intensity: " + str(state.intensity) + " in/hr",
        LineBreak(),
        "Pipe: " + str(state.diameter) + " in " + state.material
        + " at " + str(state.slope_percent) + "% slope",
        HorizontalRule(),
        Bold("Calculated"),
        LineBreak(),
        "Design flow: " + str(round(state.design_flow, 2)) + " cfs",
        LineBreak(),
        "Pipe full-flow capacity: " + str(round(state.capacity, 2)) + " cfs",
        LineBreak(),
        "Percent of capacity used: " + str(round(state.percent_used, 1)) + "%",
        LineBreak(),
        "Full-flow velocity: " + str(round(state.velocity, 2)) + " ft/s",
        LineBreak(),
        "(Pipes are considered adequate here when the flow uses "
        + str(int(ALLOWED_PERCENT_FULL)) + "% of capacity or less.)",
    ]

    if state.verdict == "UNDERSIZED":
        content.append(HorizontalRule())
        if state.recommended > 0:
            content.append("Recommended minimum diameter: "
                           + str(state.recommended) + " inches")
        else:
            content.append("No standard size up to 72 inches is large enough "
                           "at this slope. Consider a steeper slope, multiple "
                           "pipes, or a box culvert (ask an engineer).")

    if len(state.warnings) > 0:
        content.append(HorizontalRule())
        content.append(Bold("Warnings"))
        for note in state.warnings:
            content.append(LineBreak())
            content.append(note)

    content += [
        HorizontalRule(),
        Button("Change Pipe", pipe_page),
        Button("Change Drainage Area", watershed_page),
        Button("Start Over", restart),
    ]
    return Page(state, content)


@route
def restart(state: State) -> Page:
    return index(new_state())

set_website_title("Culvert Size Checker")
set_site_information(
    author="Jacob Burgos",
    description="Checks whether a drainage pipe or culvert is big enough.",
    sources="Rational Method and Manning's equation. Built with Drafter and LLM help.",
    planning=["fnlprojectcisc0.pdf", "Designphase.docx"],
    links=["https://github.com/jsburgos07/Culvert-Checker"]
)
hide_debug_information()
set_website_framed(False)
start_server(new_state())
