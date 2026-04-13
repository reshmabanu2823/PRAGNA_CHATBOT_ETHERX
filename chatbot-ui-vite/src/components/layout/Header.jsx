import ProfileDropdown from "../ui/ProfileDropdown";
import SidebarToggle from "../ui/SidebarToggle";
import ChatModeSelector from "../chat/ChatModeSelector";
import GlobalIntelligencePanel from "../ui/GlobalIntelligencePanel";
import pragnaLogo from "../../assets/pragna-logo-full.png";

export default function Header({ onLogout, activeView = "chat", onChangeView }) {
  const isDashboard = activeView === "dashboard";

  return (
    <>
      <div className="header">
        <div className="header-left">
          <SidebarToggle />
          <img src={pragnaLogo} alt="Pragna-1 A" className="header-logo header-logo-full" />
        </div>

        <div className="header-right">
          <button
            className="header-view-toggle"
            onClick={() => onChangeView(isDashboard ? "chat" : "dashboard")}
            title="Shortcut: Ctrl+Shift+D"
          >
            {isDashboard ? "Back to Chat" : "Open Dashboard (Ctrl+Shift+D)"}
          </button>
          <ProfileDropdown onLogout={onLogout} />
        </div>
      </div>
      {!isDashboard && (
        <div className="header-modes">
          <ChatModeSelector />
          <GlobalIntelligencePanel />
        </div>
      )}
    </>
  );
}
