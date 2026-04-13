import { useContext } from "react";
import { ChatContext } from "../../context/ChatContext";

export default function SidebarToggle() {
    const { toggleSidebar } = useContext(ChatContext);

    return (
        <button
            className="sidebar-toggle"
            onClick={toggleSidebar}
            title="Toggle sidebar"
        >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
        </button>
    );
}
