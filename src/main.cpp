#include <algorithm>
#include <array>
#include <format>
#include <string>
#include <typeinfo>
#include <unordered_set>
#include <vector>
#include <lua.hpp>

#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/desktop/state/FocusState.hpp>
#include <hyprland/src/desktop/view/Window.hpp>
#include <hyprland/src/managers/fullscreen/FullscreenController.hpp>
#include <hyprland/src/layout/algorithm/Algorithm.hpp>
#include <hyprland/src/layout/space/Space.hpp>
#include <hyprland/src/layout/target/Target.hpp>
#include <hyprland/src/output/Monitor.hpp>

// Hyprland exposes the dwindle node type but keeps its node collection private.
// A derived algorithm needs that collection to collapse hidden branches without
// deleting them. This is the documented escape hatch for plugin-only internals.
#define private public
#include <hyprland/src/layout/algorithm/tiled/dwindle/DwindleAlgorithm.hpp>
#undef private

using namespace Layout;
using namespace Layout::Tiled;

namespace {
HANDLE g_handle = nullptr;
std::vector<PHLWINDOWREF> g_minimized;

bool isMinimized(const PHLWINDOW& window) {
    if (!window)
        return false;

    return std::ranges::any_of(g_minimized, [&window](const auto& candidate) {
        return candidate.lock() == window;
    });
}

void pruneHistory() {
    std::erase_if(g_minimized, [](const auto& candidate) { return candidate.expired(); });
}

void notify(const std::string& message) {
    HyprlandAPI::addNotificationV2(g_handle, {
        {"text", message},
        {"time", uint64_t{2200}},
        {"color", CHyprColor{0}},
    });
}

class CTileKeeperAlgorithm final : public CDwindleAlgorithm {
  public:
    std::optional<std::string> layoutName() const override {
        return "tilekeeper";
    }

    void recalculate([[maybe_unused]] eRecalculateReason reason = RECALCULATE_REASON_UNKNOWN) override {
        if (!m_parent || !m_parent->space())
            return;

        pruneHistory();
        const auto workspace = m_parent->space()->workspace();
        if (!workspaceHasMinimized(workspace) || Fullscreen::controller()->hasFullscreen(workspace, true)) {
            CDwindleAlgorithm::recalculate(reason);
            return;
        }

        const auto root = rootNode();
        if (!root)
            return;

        layoutVisibleTree(root, m_parent->space()->workArea());
    }

    void newTarget(SP<ITarget> target) override {
        CDwindleAlgorithm::newTarget(target);
        recalculate();
    }

    void movedTarget(SP<ITarget> target, std::optional<Vector2D> focalPoint = std::nullopt) override {
        CDwindleAlgorithm::movedTarget(target, focalPoint);
        recalculate();
    }

    void removeTarget(SP<ITarget> target) override {
        CDwindleAlgorithm::removeTarget(target);
        recalculate();
    }

    void resizeTarget(const Vector2D& delta, SP<ITarget> target, eRectCorner corner = CORNER_NONE) override {
        CDwindleAlgorithm::resizeTarget(delta, target, corner);
        recalculate();
    }

    void swapTargets(SP<ITarget> first, SP<ITarget> second) override {
        CDwindleAlgorithm::swapTargets(first, second);
        recalculate();
    }

    void moveTargetInDirection(SP<ITarget> target, Math::eDirection direction, bool silent) override {
        CDwindleAlgorithm::moveTargetInDirection(target, direction, silent);
        recalculate();
    }

    Config::ErrorResult layoutMsg(const std::string_view& message) override {
        auto result = CDwindleAlgorithm::layoutMsg(message);
        recalculate();
        return result;
    }

    PHLWINDOW firstVisibleWindow() const {
        for (const auto& node : m_dwindleNodesData) {
            if (!node || node->isNode)
                continue;
            const auto target = node->pTarget.lock();
            const auto window = target ? target->window() : nullptr;
            if (window && Desktop::View::validMapped(window) && !isMinimized(window))
                return window;
        }
        return nullptr;
    }

  private:
    static bool workspaceHasMinimized(const PHLWORKSPACE& workspace) {
        return std::ranges::any_of(g_minimized, [&workspace](const auto& candidate) {
            const auto window = candidate.lock();
            return window && window->m_workspace == workspace;
        });
    }

    SP<SDwindleNodeData> rootNode() const {
        for (const auto& node : m_dwindleNodesData) {
            if (node && !node->pParent)
                return node;
        }
        return nullptr;
    }

    bool hasVisibleLeaf(const SP<SDwindleNodeData>& node) const {
        if (!node)
            return false;
        if (!node->isNode) {
            const auto target = node->pTarget.lock();
            const auto window = target ? target->window() : nullptr;
            return window && Desktop::View::validMapped(window) && !isMinimized(window);
        }
        return hasVisibleLeaf(node->children[0].lock()) || hasVisibleLeaf(node->children[1].lock());
    }

    void layoutVisibleTree(const SP<SDwindleNodeData>& node, const CBox& box) {
        if (!node)
            return;

        node->box = box;
        if (!node->isNode) {
            const auto target = node->pTarget.lock();
            const auto window = target ? target->window() : nullptr;
            if (target && window && !isMinimized(window))
                target->setPositionGlobal(box);
            return;
        }

        const auto first  = node->children[0].lock();
        const auto second = node->children[1].lock();
        const bool firstVisible  = hasVisibleLeaf(first);
        const bool secondVisible = hasVisibleLeaf(second);

        if (firstVisible && !secondVisible) {
            layoutVisibleTree(first, box);
            return;
        }
        if (!firstVisible && secondVisible) {
            layoutVisibleTree(second, box);
            return;
        }
        if (!firstVisible && !secondVisible)
            return;

        CBox firstBox;
        CBox secondBox;
        if (node->splitTop) {
            const double firstHeight = box.h / 2.0 * node->splitRatio;
            firstBox  = {box.x, box.y, box.w, firstHeight};
            secondBox = {box.x, box.y + firstHeight, box.w, box.h - firstHeight};
        } else {
            const double firstWidth = box.w / 2.0 * node->splitRatio;
            firstBox  = {box.x, box.y, firstWidth, box.h};
            secondBox = {box.x + firstWidth, box.y, box.w - firstWidth, box.h};
        }

        layoutVisibleTree(first, firstBox.noNegativeSize());
        layoutVisibleTree(second, secondBox.noNegativeSize());
    }
};

CTileKeeperAlgorithm* algorithmForWorkspace(const PHLWORKSPACE& workspace) {
    if (!workspace || !workspace->m_space || !workspace->m_space->algorithm())
        return nullptr;
    return dynamic_cast<CTileKeeperAlgorithm*>(workspace->m_space->algorithm()->tiledAlgo().get());
}

SDispatchResult failure(std::string message) {
    notify(message);
    return {.success = false, .error = std::move(message)};
}

SDispatchResult minimizeTile(std::string) {
    pruneHistory();
    const auto window = Desktop::focusState()->window();
    if (!window || !Desktop::View::validMapped(window))
        return failure("Tile Keeper: no active window");
    if (window->m_isFloating)
        return failure("Tile Keeper: floating windows are not tiles");
    if (!window->layoutTarget() || window->layoutTarget()->type() == TARGET_TYPE_GROUP)
        return failure("Tile Keeper: grouped windows are not supported yet");
    if (Fullscreen::controller()->isFullscreen(window))
        return failure("Tile Keeper: leave fullscreen before minimizing");
    if (isMinimized(window))
        return failure("Tile Keeper: window is already minimized");

    auto* const algorithm = algorithmForWorkspace(window->m_workspace);
    if (!algorithm)
        return failure("Tile Keeper: current workspace is not using tilekeeper");

    g_minimized.emplace_back(window);
    window->setHidden(true);
    window->m_workspace->m_space->recalculate();

    if (const auto next = algorithm->firstVisibleWindow())
        Desktop::focusState()->fullWindowFocus(next, Desktop::FOCUS_REASON_KEYBIND);
    else
        Desktop::focusState()->resetWindowFocus();

    notify(std::format("Minimized: {}", window->m_title));
    return {};
}

SDispatchResult restoreTile(std::string) {
    pruneHistory();
    const auto monitor = Desktop::focusState()->monitor();
    const auto workspace = monitor ? monitor->m_activeWorkspace : nullptr;
    if (!workspace)
        return failure("Tile Keeper: no active workspace");
    if (!algorithmForWorkspace(workspace))
        return failure("Tile Keeper: current workspace is not using tilekeeper");

    auto it = std::find_if(g_minimized.rbegin(), g_minimized.rend(), [&workspace](const auto& candidate) {
        const auto window = candidate.lock();
        return window && window->m_workspace == workspace;
    });
    if (it == g_minimized.rend())
        return failure("Tile Keeper: no minimized tile on this workspace");

    const auto window = it->lock();
    g_minimized.erase(std::next(it).base());
    window->setHidden(false);
    workspace->m_space->recalculate();
    Desktop::focusState()->fullWindowFocus(window, Desktop::FOCUS_REASON_KEYBIND);
    notify(std::format("Restored: {}", window->m_title));
    return {};
}
} // namespace

APICALL EXPORT std::string PLUGIN_API_VERSION() {
    return HYPRLAND_API_VERSION;
}

APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE handle) {
    if (std::string{__hyprland_api_get_hash()} != __hyprland_api_get_client_hash())
        throw std::runtime_error("Tile Keeper: rebuild against the running Hyprland ABI");
    g_handle = handle;

    if (!HyprlandAPI::addTiledAlgo(handle, "tilekeeper", &typeid(CTileKeeperAlgorithm), [] {
            return makeUnique<CTileKeeperAlgorithm>();
        }))
        throw std::runtime_error("failed to register tilekeeper layout");

    if (!HyprlandAPI::addDispatcherV2(handle, "tilekeeper:minimize", minimizeTile) ||
        !HyprlandAPI::addDispatcherV2(handle, "tilekeeper:restore", restoreTile))
        throw std::runtime_error("failed to register tilekeeper dispatchers");

    if (!HyprlandAPI::addLuaFunction(handle, "tilekeeper", "minimize", [](lua_State* L) -> int {
            const auto result = minimizeTile("");
            lua_pushboolean(L, result.success);
            return 1;
        }) ||
        !HyprlandAPI::addLuaFunction(handle, "tilekeeper", "restore", [](lua_State* L) -> int {
            const auto result = restoreTile("");
            lua_pushboolean(L, result.success);
            return 1;
        }))
        throw std::runtime_error("failed to register tilekeeper Lua functions");

    return {
        "hyprtilekeeper",
        "True minimize/restore for dwindle tiles",
        "cday",
        "0.2.0",
    };
}

APICALL EXPORT void PLUGIN_EXIT() {
    for (const auto& reference : g_minimized) {
        if (const auto window = reference.lock())
            window->setHidden(false);
    }
    g_minimized.clear();
    g_handle = nullptr;
}
