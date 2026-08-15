from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import cache


ALLOWED_IMPORT_ROOTS = {"manim", "numpy", "math"}
BANNED_NAMES = {
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "vars",
    "help",
    "exit",
    "quit",
}
BANNED_ATTRIBUTES = {
    "add_sound",
    "system",
    "popen",
    "spawn",
    "fork",
    "connect",
    "request",
    "urlopen",
    "read_text",
    "write_text",
    "read_bytes",
    "write_bytes",
    "unlink",
    "remove",
    "rmdir",
    "mkdir",
    "environ",
}
MANIMGL_NAMES = {"ShowCreation", "GraphScene", "TexMobject", "TextMobject", "get_graph"}

# Real Manim API that this pipeline still rejects. The generic "unknown attribute" text
# leaves the repair prompt guessing, so these rejections explain the actual reason.
EXPLAINED_ATTRIBUTES = {
    "add_coordinates": (
        "add_coordinates is not allowed here because axis_config already sets include_numbers=True, "
        "so the numbers would be drawn twice. Remove the call."
    ),
}

@cache
def manim_namespace() -> frozenset[str]:
    """Every public name the installed Manim actually exports.

    Checking against the real namespace catches hallucinated and ManimGL-only names, which
    is the point of the check, without a hand-maintained list that rejects valid API such as
    Cross or BraceBetweenPoints and burns one of only two repair attempts. Falls back to the
    curated list below when Manim is not importable.
    """
    try:
        import manim
    except ImportError:
        return frozenset()
    return frozenset(name for name in dir(manim) if not name.startswith("_"))


# Fallback list used only when Manim cannot be imported. It also documents the core surface
# these lessons are expected to stay within.
ALLOWED_GLOBAL_NAMES = {
    "Scene",
    "Axes",
    "Text",
    "MathTex",
    "VGroup",
    "Group",
    "VMobject",
    "Mobject",
    "Dot",
    "Line",
    "DashedLine",
    "Arrow",
    "DoubleArrow",
    "Polygon",
    "Rectangle",
    "RoundedRectangle",
    "Square",
    "Circle",
    "Triangle",
    "Brace",
    "BraceLabel",
    "SurroundingRectangle",
    # Drawing primitives the curated catalog genuinely needs: Cross for the
    # error-analysis method, angles for the geometry topics.
    "Cross",
    "Underline",
    "Angle",
    "RightAngle",
    "Arc",
    "Ellipse",
    "ValueTracker",
    "always_redraw",
    "Create",
    "Write",
    "FadeIn",
    "FadeOut",
    "Transform",
    "ReplacementTransform",
    "TransformMatchingTex",
    "AnimationGroup",
    "Succession",
    "GrowArrow",
    "GrowFromCenter",
    "Indicate",
    "Circumscribe",
    "LaggedStart",
    "FadeTransform",
    "DrawBorderThenFill",
    "Flash",
    "Wiggle",
    "ORIGIN",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "UL",
    "UR",
    "DL",
    "DR",
    "PI",
    "TAU",
    "DEGREES",
    "WHITE",
    "BLACK",
    "GRAY",
    "GREY",
    "BLUE",
    "GREEN",
    "RED",
    "YELLOW",
    "TEAL",
    "PURPLE",
    "ORANGE",
}

# Kept as documentation of the Manim surface these lessons normally use. It is deliberately
# not enforced as an allowlist: attribute access is not the safety boundary (imports, the
# banned names below, dunder access and the credential-scrubbed subprocess are), while
# rejecting every unlisted attribute made valid Manim API such as axes.x_axis or
# animations.append(...) fail validation and consume one of only two repair attempts.
DOCUMENTED_ATTRIBUTES = {
    "play",
    "wait",
    "add",
    "clear",
    "next_to",
    "to_edge",
    "to_corner",
    "shift",
    "move_to",
    "scale",
    "scale_to_fit_width",
    "scale_to_fit_height",
    "set_color",
    "set_fill",
    "set_stroke",
    "set_opacity",
    "set_z_index",
    "arrange",
    "arrange_in_grid",
    "align_to",
    "rotate",
    "stretch",
    "plot",
    "c2p",
    "coords_to_point",
    "p2c",
    "get_center",
    "get_start",
    "get_end",
    "get_left",
    "get_right",
    "get_top",
    "get_bottom",
    "get_corner",
    "get_value",
    "set_value",
    # Read-only geometry properties needed to clamp a group into the safe frame band.
    "height",
    "width",
    "animate",
    "mobjects",
    "copy",
    "become",
    "get_axis_labels",
    "get_x_axis_label",
    "get_y_axis_label",
    "get_vertical_line",
    "get_horizontal_line",
    "point_from_proportion",
    "set_points_as_corners",
    "append_points",
    "add_updater",
    "remove_updater",
    "suspend_updating",
    "resume_updating",
    "set",
    "camera",
    "background_color",
    "time",
    # Plain Python container and string methods. These reach no filesystem, process or
    # network API, and rejecting them made ordinary code such as animations.append(...)
    # fail validation and consume a repair attempt.
    "append",
    "extend",
    "insert",
    "join",
    "format",
    "items",
    "keys",
    "values",
    "array",
    "linspace",
    "sin",
    "cos",
    "tan",
    "sqrt",
    "abs",
}

ALLOWED_BUILTINS = {
    "range",
    "len",
    "min",
    "max",
    "sum",
    "abs",
    "round",
    "enumerate",
    "zip",
    "float",
    "int",
    "str",
    "list",
    "tuple",
    "dict",
    "bool",
    "True",
    "False",
    "None",
    "super",
    # Pure, side-effect-free builtins. getattr and setattr stay banned above, because those
    # are the ones that could reach an attribute the rules exclude.
    "isinstance",
    "sorted",
    "reversed",
    "map",
    "filter",
    "any",
    "all",
    "divmod",
    "pow",
    "set",
}


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)


class LocalNameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            self.names.add(node.id)

    def visit_arg(self, node: ast.arg) -> None:
        self.names.add(node.arg)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)
        self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> None:
        self.names.add(node.asname or node.name.split(".")[0])


class SafetyVisitor(ast.NodeVisitor):
    def __init__(self, known_names: set[str]) -> None:
        self.known_names = known_names | (manim_namespace() or ALLOWED_GLOBAL_NAMES) | ALLOWED_BUILTINS
        self.issues: list[str] = []

    def issue(self, node: ast.AST, message: str) -> None:
        self.issues.append(f"Line {getattr(node, 'lineno', '?')}: {message}")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] not in ALLOWED_IMPORT_ROOTS:
                self.issue(node, f"Import not allowed: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root not in ALLOWED_IMPORT_ROOTS:
            self.issue(node, f"Import not allowed: {node.module}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in BANNED_NAMES:
            self.issue(node, f"Forbidden name: {node.id}")
        if node.id in MANIMGL_NAMES:
            self.issue(node, f"ManimGL name not allowed: {node.id}")
        if isinstance(node.ctx, ast.Load) and node.id not in self.known_names:
            self.issue(node, f"Unknown or disallowed API name: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BANNED_ATTRIBUTES:
            self.issue(node, f"Forbidden attribute access: {node.attr}")
        if node.attr in MANIMGL_NAMES:
            self.issue(node, f"ManimGL attribute not allowed: {node.attr}")
        if node.attr in EXPLAINED_ATTRIBUTES:
            self.issue(node, EXPLAINED_ATTRIBUTES[node.attr])
        # Dunder access is the one attribute route that can escape the sandbox, for example
        # through __class__ or __globals__ to reach builtins the import rules exclude.
        if node.attr.startswith("__"):
            self.issue(node, f"Access to internal attributes is not allowed: {node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr

        if call_name in BANNED_NAMES or call_name in BANNED_ATTRIBUTES:
            self.issue(node, f"Forbidden call: {call_name}")
        if call_name in MANIMGL_NAMES:
            self.issue(node, f"ManimGL call not allowed: {call_name}")

        if call_name == "MathTex":
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    value = argument.value
                    if re.search(r"[äöüÄÖÜß]", value):
                        self.issue(node, "Umlauts and ß are not allowed inside MathTex.")
                    if "\\text{" in value:
                        self.issue(node, "LaTeX \\text{} is not allowed inside MathTex.")
                    prose_commands = re.findall(
                        r"\\(?:mathrm|textrm|mbox|operatorname)\s*\{([^{}]*)\}",
                        value,
                    )
                    if any(len(re.sub(r"[^A-Za-z]", "", content)) > 3 for content in prose_commands):
                        self.issue(node, "Prose inside LaTeX font commands is not allowed in MathTex.")

        if call_name == "Text":
            for keyword in node.keywords:
                if keyword.arg == "font_size" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, (int, float)) and keyword.value.value < 28:
                        self.issue(node, "Text font_size must not be smaller than 28.")
        self.generic_visit(node)


def _originates_from_mathtex(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "MathTex":
            return True
        if isinstance(node.func, ast.Attribute):
            return _originates_from_mathtex(node.func.value)
    if isinstance(node, ast.Attribute):
        return _originates_from_mathtex(node.value)
    return False


def _mathtex_bindings(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not _originates_from_mathtex(value):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _fragile_mathtex_indexes(tree: ast.AST, bindings: set[str]) -> list[str]:
    issues: list[str] = []
    reported_lines: set[int | str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        base = node.value
        while isinstance(base, ast.Subscript):
            base = base.value
        direct_call = _originates_from_mathtex(base)
        bound_name = isinstance(base, ast.Name) and base.id in bindings
        if direct_call or bound_name:
            line = getattr(node, "lineno", "?")
            if line in reported_lines:
                continue
            reported_lines.add(line)
            issues.append(
                f"Line {line}: MathTex must not be split by numeric index; "
                "use separate mobjects or highlight the whole formula."
            )
    return issues


def _has_final_wait(construct: ast.FunctionDef) -> bool:
    if not construct.body:
        return False
    final = construct.body[-1]
    if not isinstance(final, ast.Expr) or not isinstance(final.value, ast.Call):
        return False
    call = final.value
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "wait":
        return False
    return bool(call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == 1)


def validate_manim_source(source: str, expected_sections: int) -> ValidationResult:
    issues: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return ValidationResult(False, [f"Python syntax error on line {error.lineno}: {error.msg}"])

    collector = LocalNameCollector()
    collector.visit(tree)
    visitor = SafetyVisitor(collector.names)
    visitor.visit(tree)
    issues.extend(visitor.issues)
    issues.extend(_fragile_mathtex_indexes(tree, _mathtex_bindings(tree)))

    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    required_classes = {"LessonVideo", "RecapCard1", "RecapCard2", "RecapCard3"}
    missing = required_classes - classes.keys()
    if missing:
        issues.append("Missing Scene classes: " + ", ".join(sorted(missing)))

    lesson = classes.get("LessonVideo")
    if lesson:
        methods = {node.name: node for node in lesson.body if isinstance(node, ast.FunctionDef)}
        construct = methods.get("construct")
        if not construct:
            issues.append("LessonVideo.construct is missing.")
        elif not _has_final_wait(construct):
            issues.append("LessonVideo.construct must end with self.wait(1).")
        for index in range(1, expected_sections + 1):
            name = f"section_{index}"
            method = methods.get(name)
            if not method:
                issues.append(f"Section method is missing: {name}(self, duration)")
                continue
            arguments = [argument.arg for argument in method.args.args]
            if arguments[:2] != ["self", "duration"]:
                issues.append(f"{name} must take the parameters self and duration.")

    return ValidationResult(valid=not issues, issues=issues)
