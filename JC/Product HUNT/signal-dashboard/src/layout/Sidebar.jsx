import "./Sidebar.css";

export default function Sidebar() {
  return (
    <div className="sidebar">
      <h2 className="logo">SignalDetector</h2>

      <nav className="menu">
        <a className="menu-item">Dashboard</a>
        <a className="menu-item active">Signals</a>
        <a className="menu-item">Companies</a>
        <a className="menu-item">Scout</a>
      </nav>

    </div>
  );
}
