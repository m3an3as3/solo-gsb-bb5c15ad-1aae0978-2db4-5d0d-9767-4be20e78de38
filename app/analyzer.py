"""依赖图解析与许可冲突分析。

- 校验用户上传的 JSON 清单
- 以项目根节点做 BFS，求出每个包的最短依赖路径
- 按许可兼容矩阵逐包判定，并汇总结果
"""

from collections import deque

from .licenses import LICENSE_INFO, POLICIES, evaluate, normalize_license


class ManifestError(ValueError):
    """清单格式不合法。"""


def validate_manifest(m):
    """校验清单结构，返回 (project, packages, edges)。

    packages: {name: {"name", "version", "license"}}
    edges:    {from_name: [to_name, ...]}
    """
    if not isinstance(m, dict):
        raise ManifestError("清单必须是 JSON 对象")

    project = m.get("project")
    if not isinstance(project, dict) or not str(project.get("name", "")).strip():
        raise ManifestError("缺少 project.name（项目根节点名称）")
    project = {
        "name": str(project["name"]).strip(),
        "version": str(project.get("version", "")),
        "license": str(project.get("license", "")),
    }

    raw_packages = m.get("packages")
    if not isinstance(raw_packages, list) or not raw_packages:
        raise ManifestError("packages 必须是非空数组")

    packages = {}
    for i, p in enumerate(raw_packages):
        if not isinstance(p, dict) or not str(p.get("name", "")).strip():
            raise ManifestError(f"packages[{i}] 缺少 name")
        name = str(p["name"]).strip()
        if name == project["name"]:
            raise ManifestError(f"packages[{i}] 的包名与项目名冲突: {name}")
        if name in packages:
            raise ManifestError(f"包名重复: {name}（当前要求同一清单内包名唯一）")
        packages[name] = {
            "name": name,
            "version": str(p.get("version", "")),
            "license": p.get("license") or "Unknown",
        }

    raw_deps = m.get("dependencies", [])
    if not isinstance(raw_deps, list):
        raise ManifestError("dependencies 必须是数组")

    edges = {}
    known = set(packages) | {project["name"]}
    for i, d in enumerate(raw_deps):
        if not isinstance(d, dict):
            raise ManifestError(f"dependencies[{i}] 必须是对象")
        frm, to = str(d.get("from", "")).strip(), str(d.get("to", "")).strip()
        if not frm or not to:
            raise ManifestError(f"dependencies[{i}] 需要 from 和 to 字段")
        for endpoint in (frm, to):
            if endpoint not in known:
                raise ManifestError(f"dependencies[{i}] 引用了未知包: {endpoint}")
        edges.setdefault(frm, [])
        if to not in edges[frm]:
            edges[frm].append(to)

    return project, packages, edges


def _shortest_paths(root, edges):
    """BFS 求根节点到每个可达节点的最短路径，返回 {node: [root, ..., node]}。"""
    dist = {root: 0}
    prev = {}
    queue = deque([root])
    while queue:
        u = queue.popleft()
        for v in edges.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                prev[v] = u
                queue.append(v)

    paths = {}
    for node in dist:
        path = [node]
        while path[-1] != root:
            path.append(prev[path[-1]])
        path.reverse()
        paths[node] = path
    return paths


def analyze(manifest, policy_key, exception_names=()):
    """执行完整分析，返回可 JSON 序列化的结果字典。"""
    if policy_key not in POLICIES:
        raise ManifestError(f"未知许可策略: {policy_key}")

    project, packages, edges = validate_manifest(manifest)
    root = project["name"]
    paths = _shortest_paths(root, edges)
    exceptions = set(exception_names)

    findings = []
    for name, pkg in packages.items():
        lic_raw = pkg["license"]
        lic_id = normalize_license(lic_raw)
        status, rule = evaluate(policy_key, lic_id)

        reachable = name in paths
        path = paths[name] if reachable else [name]

        exempted = name in exceptions and status != "ok"
        findings.append({
            "package": name,
            "version": pkg["version"],
            "license_raw": lic_raw,
            "license": lic_id,
            "category": LICENSE_INFO[lic_id]["category"],
            "status": "exempted" if exempted else status,
            "original_status": status,
            "rule": rule,
            "path": path,
            "depth": len(path) - 1,
            "reachable": reachable,
            "exempted": exempted,
        })

    order = {"conflict": 0, "warning": 1, "exempted": 2, "ok": 3}
    findings.sort(key=lambda f: (order[f["status"]], f["depth"], f["package"]))

    summary = {
        "total": len(findings),
        "ok": sum(1 for f in findings if f["status"] == "ok"),
        "warning": sum(1 for f in findings if f["status"] == "warning"),
        "conflict": sum(1 for f in findings if f["status"] == "conflict"),
        "exempted": sum(1 for f in findings if f["status"] == "exempted"),
        "unreachable": sum(1 for f in findings if not f["reachable"]),
    }

    return {
        "project": project,
        "policy": policy_key,
        "policy_label": POLICIES[policy_key]["label"],
        "summary": summary,
        "findings": findings,
    }
