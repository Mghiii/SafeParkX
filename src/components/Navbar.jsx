import { Link } from "react-router-dom";
import "./navbar.css";

export default function Navbar() {
  return (
    <div className="navbar-container">
      <nav className="navbar">
        <div class="elem1">
          <h1>LOGO</h1>
        </div>
        <div class="elem2">
          <Link to="/Login" className="logout">
            Logout
          </Link>
          <img src="/images/admin.png" alt="admin" className="admin-img" />
        </div>
      </nav>
    </div>
  );
}
