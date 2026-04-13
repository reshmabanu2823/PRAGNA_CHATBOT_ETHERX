import Sidebar from "./Sidebar";
import Header from "./Header";

export default function MainLayout({ children, onLogout, activeView, onChangeView }) {
  return (
    <div className="layout">
      <Sidebar onLogout={onLogout} />
      <div className="main">
        <Header onLogout={onLogout} activeView={activeView} onChangeView={onChangeView} />
        {children}
      </div>
    </div>
  );
}
