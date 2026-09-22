"""许可证识别、名称规范化与项目许可策略兼容矩阵。

矩阵以「规则列表」表达：每条规则形如
    (命中的许可证集合, 判定状态, 规则编号, 规则说明)
按声明顺序匹配，未命中任何规则时视为兼容（ok）。
"""

OK = "ok"
WARNING = "warning"
CONFLICT = "conflict"
EXEMPTED = "exempted"  # 仅用于展示：被人工确认豁免的冲突/告警

# 许可证元数据，category 用于界面展示
LICENSE_INFO = {
    "MIT":          {"category": "permissive"},
    "ISC":          {"category": "permissive"},
    "0BSD":         {"category": "permissive"},
    "BSD-2-Clause": {"category": "permissive"},
    "BSD-3-Clause": {"category": "permissive"},
    "Apache-2.0":   {"category": "permissive"},
    "Unlicense":    {"category": "public-domain"},
    "CC0-1.0":      {"category": "public-domain"},
    "MPL-2.0":      {"category": "weak-copyleft"},
    "EPL-2.0":      {"category": "weak-copyleft"},
    "LGPL-2.1":     {"category": "weak-copyleft"},
    "LGPL-3.0":     {"category": "weak-copyleft"},
    "GPL-2.0":      {"category": "strong-copyleft"},
    "GPL-3.0":      {"category": "strong-copyleft"},
    "AGPL-3.0":     {"category": "network-copyleft"},
    "CC-BY-SA-4.0": {"category": "strong-copyleft"},
    "Proprietary":  {"category": "proprietary"},
    "Unknown":      {"category": "unknown"},
}

# 常见写法别名 -> 规范许可证 ID
_ALIASES = {
    "mit": "MIT", "mit license": "MIT", "the mit license": "MIT", "expat": "MIT",
    "isc": "ISC",
    "0bsd": "0BSD", "bsd-0-clause": "0BSD",
    "bsd": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause",
    "new bsd": "BSD-3-Clause", "modified bsd": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause", "bsd 2-clause": "BSD-2-Clause", "simplified bsd": "BSD-2-Clause",
    "apache": "Apache-2.0", "apache-2.0": "Apache-2.0", "apache 2.0": "Apache-2.0",
    "apache 2": "Apache-2.0", "apache license 2.0": "Apache-2.0", "asl 2.0": "Apache-2.0",
    "unlicense": "Unlicense",
    "cc0": "CC0-1.0", "cc0-1.0": "CC0-1.0", "cc0 1.0": "CC0-1.0",
    "mpl-2.0": "MPL-2.0", "mpl 2.0": "MPL-2.0", "mpl2": "MPL-2.0", "mplv2": "MPL-2.0",
    "epl-2.0": "EPL-2.0", "epl 2.0": "EPL-2.0", "epl2": "EPL-2.0",
    "lgpl": "LGPL-3.0", "lgpl-3.0": "LGPL-3.0", "lgplv3": "LGPL-3.0", "lgpl 3": "LGPL-3.0",
    "lgpl-2.1": "LGPL-2.1", "lgplv2.1": "LGPL-2.1", "lgpl 2.1": "LGPL-2.1",
    "gpl-2.0": "GPL-2.0", "gplv2": "GPL-2.0", "gpl2": "GPL-2.0", "gpl 2": "GPL-2.0",
    "gpl-2.0-only": "GPL-2.0", "gpl-2.0-or-later": "GPL-2.0",
    "gpl-3.0": "GPL-3.0", "gplv3": "GPL-3.0", "gpl3": "GPL-3.0", "gpl 3": "GPL-3.0",
    "gpl-3.0-only": "GPL-3.0", "gpl-3.0-or-later": "GPL-3.0",
    "agpl-3.0": "AGPL-3.0", "agplv3": "AGPL-3.0", "agpl": "AGPL-3.0", "agpl-3.0-only": "AGPL-3.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0", "cc by-sa 4.0": "CC-BY-SA-4.0",
    "proprietary": "Proprietary", "commercial": "Proprietary", "closed-source": "Proprietary",
    "unknown": "Unknown", "": "Unknown", "none": "Unknown", "n/a": "Unknown",
}


def normalize_license(raw):
    """把用户填写的许可证字符串规范化为内置许可证 ID，无法识别时归为 Unknown。"""
    if raw is None:
        return "Unknown"
    key = str(raw).strip().lower().rstrip("+")
    key = " ".join(key.split())
    return _ALIASES.get(key, "Unknown")


# 兼容矩阵：项目许可策略 -> 规则列表
POLICIES = {
    "proprietary": {
        "label": "商业闭源（Proprietary）",
        "description": "项目以专有许可分发（含 SaaS 形态），不允许 Copyleft 传染",
        "rules": [
            ({"AGPL-3.0"}, CONFLICT, "R-PRO-01",
             "AGPL-3.0 具有网络 Copyleft：即使以 SaaS 方式提供服务也须开源整个衍生作品，闭源商业项目禁止使用"),
            ({"GPL-2.0", "GPL-3.0"}, CONFLICT, "R-PRO-02",
             "强 Copyleft（GPL）会传染至整个分发作品，闭源商业项目禁止链接/分发 GPL 组件"),
            ({"CC-BY-SA-4.0"}, CONFLICT, "R-PRO-03",
             "CC-BY-SA-4.0 要求衍生作品以相同方式共享，与闭源分发不兼容"),
            ({"LGPL-2.1", "LGPL-3.0"}, WARNING, "R-PRO-04",
             "LGPL 允许商业使用，但须保证用户可替换该库（动态链接或提供可重链接的目标文件），需人工确认链接方式"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-PRO-05",
             "弱 Copyleft：对该组件源文件的修改须以相同许可公开，需确认未修改或已公开修改部分"),
            ({"Proprietary"}, WARNING, "R-PRO-06",
             "第三方专有组件：需确认已获得覆盖当前分发场景的商业授权"),
            ({"Unknown"}, WARNING, "R-PRO-07",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
    "mit": {
        "label": "宽松开源（MIT/BSD 类项目）",
        "description": "项目以 MIT/BSD 等宽松许可发布，不能接受 Copyleft 传染",
        "rules": [
            ({"AGPL-3.0"}, CONFLICT, "R-MIT-01",
             "AGPL-3.0 的网络 Copyleft 会要求整个项目以 AGPL 开源，与宽松许可策略冲突"),
            ({"GPL-2.0", "GPL-3.0"}, CONFLICT, "R-MIT-02",
             "强 Copyleft（GPL）会要求整个衍生作品转为 GPL，与 MIT/BSD 类宽松许可策略冲突"),
            ({"CC-BY-SA-4.0"}, WARNING, "R-MIT-03",
             "CC-BY-SA 的相同方式共享条款不适合代码项目，需人工确认使用范围（仅限文档/素材时可接受）"),
            ({"LGPL-2.1", "LGPL-3.0"}, WARNING, "R-MIT-04",
             "LGPL 组件须以可替换方式（动态链接）使用，需人工确认链接方式"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-MIT-05",
             "弱 Copyleft：对该组件源文件的修改须以相同许可公开，需确认未修改或已公开修改部分"),
            ({"Proprietary"}, CONFLICT, "R-MIT-06",
             "开源项目不得依赖未获开源授权的专有组件"),
            ({"Unknown"}, WARNING, "R-MIT-07",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
    "apache-2.0": {
        "label": "Apache-2.0 项目",
        "description": "项目以 Apache-2.0 发布，依赖不得与 Apache-2.0 不兼容",
        "rules": [
            ({"AGPL-3.0"}, CONFLICT, "R-AP-01",
             "AGPL-3.0 的网络 Copyleft 会要求整个项目以 AGPL 开源，与 Apache-2.0 策略冲突"),
            ({"GPL-2.0"}, CONFLICT, "R-AP-02",
             "GPL-2.0 与 Apache-2.0 互不兼容（专利条款冲突），不得组合进同一衍生作品"),
            ({"GPL-3.0"}, CONFLICT, "R-AP-03",
             "GPL-3.0 会要求整个衍生作品转为 GPL-3.0，与 Apache-2.0 项目策略冲突"),
            ({"CC-BY-SA-4.0"}, WARNING, "R-AP-04",
             "CC-BY-SA 的相同方式共享条款不适合代码项目，需人工确认使用范围"),
            ({"LGPL-2.1", "LGPL-3.0"}, WARNING, "R-AP-05",
             "LGPL 组件须以可替换方式（动态链接）使用，需人工确认链接方式"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-AP-06",
             "弱 Copyleft：对该组件源文件的修改须以相同许可公开，需确认未修改或已公开修改部分"),
            ({"Proprietary"}, CONFLICT, "R-AP-07",
             "开源项目不得依赖未获开源授权的专有组件"),
            ({"Unknown"}, WARNING, "R-AP-08",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
    "gpl-2.0": {
        "label": "GPL-2.0 项目",
        "description": "项目以 GPL-2.0 发布，依赖须与 GPLv2 兼容",
        "rules": [
            ({"Apache-2.0"}, CONFLICT, "R-G2-01",
             "Apache-2.0 的专利授权/终止条款与 GPL-2.0 不兼容（FSF 结论），不得并入 GPLv2 项目"),
            ({"GPL-3.0", "LGPL-3.0"}, CONFLICT, "R-G2-02",
             "GPL-3.0/LGPL-3.0 附加条款与 GPL-2.0 互不兼容，GPLv2 项目无法并入"),
            ({"AGPL-3.0"}, CONFLICT, "R-G2-03",
             "AGPL-3.0 与 GPL-2.0 不兼容，不得并入 GPLv2 项目"),
            ({"CC-BY-SA-4.0"}, WARNING, "R-G2-04",
             "CC-BY-SA 与 GPL 系列不兼容，仅限独立文档/素材使用，需人工确认"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-G2-05",
             "弱 Copyleft 与 GPL 组合时须确认相关文件未声明「不兼容次级许可」，需人工核实"),
            ({"Proprietary"}, CONFLICT, "R-G2-06",
             "GPL 项目的衍生作品须整体以 GPL 发布，不得混入专有组件"),
            ({"Unknown"}, WARNING, "R-G2-07",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
    "gpl-3.0": {
        "label": "GPL-3.0 项目",
        "description": "项目以 GPL-3.0 发布，依赖须与 GPLv3 兼容",
        "rules": [
            ({"GPL-2.0"}, CONFLICT, "R-G3-01",
             "GPL-2.0（仅 v2）与 GPL-3.0 互不兼容，GPLv3 项目无法并入 GPLv2-only 组件"),
            ({"CC-BY-SA-4.0"}, WARNING, "R-G3-02",
             "CC-BY-SA-4.0 仅可单向兼容进 GPLv3 的素材场景，需人工确认使用范围"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-G3-03",
             "弱 Copyleft 与 GPL 组合时须确认相关文件未声明「不兼容次级许可」，需人工核实"),
            ({"Proprietary"}, CONFLICT, "R-G3-04",
             "GPL 项目的衍生作品须整体以 GPL 发布，不得混入专有组件"),
            ({"Unknown"}, WARNING, "R-G3-05",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
    "agpl-3.0": {
        "label": "AGPL-3.0 项目",
        "description": "项目以 AGPL-3.0 发布（网络服务亦须开源），依赖须与 AGPLv3 兼容",
        "rules": [
            ({"GPL-2.0"}, CONFLICT, "R-AG-01",
             "GPL-2.0（仅 v2）与 AGPL-3.0 互不兼容，无法并入 AGPLv3 项目"),
            ({"CC-BY-SA-4.0"}, WARNING, "R-AG-02",
             "CC-BY-SA 与 AGPL 组合需人工确认使用范围（仅限独立文档/素材时可接受）"),
            ({"MPL-2.0", "EPL-2.0"}, WARNING, "R-AG-03",
             "弱 Copyleft 与 AGPL 组合时须确认相关文件未声明「不兼容次级许可」，需人工核实"),
            ({"Proprietary"}, CONFLICT, "R-AG-04",
             "AGPL 项目的衍生作品须整体以 AGPL 发布，不得混入专有组件"),
            ({"Unknown"}, WARNING, "R-AG-05",
             "许可证未知：无法确认合规性，需人工核实"),
        ],
    },
}

_DEFAULT_RULE = (OK, "R-OK-01", "宽松/公有领域许可证，与当前项目许可策略兼容")


def evaluate(policy_key, license_id):
    """按兼容矩阵评估 (项目策略, 依赖许可证)，返回 (状态, 规则描述)。"""
    policy = POLICIES[policy_key]
    for license_set, status, rule_id, text in policy["rules"]:
        if license_id in license_set:
            return status, f"{rule_id} · {text}"
    status, rule_id, text = _DEFAULT_RULE
    return status, f"{rule_id} · {text}"
