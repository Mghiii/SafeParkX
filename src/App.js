import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./App.css";
import Parking from "./pages/Parking";
import Login from "./pages/Login";

function App() {
  return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Parking />} />
          <Route path="/Login" element={<Login />} />
        </Routes>
      </BrowserRouter>
  );
}

export default App;
