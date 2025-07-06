import React from "react";
import "./park.css";

export default function Park() {
  return (
    <div>
      <div className="titre">
        <h1>Gestion de Parking :</h1>
      </div>
      <div className="parking">
        <div className="ent">
          <div className="entrer"></div>
          <i class="bi bi-caret-right"></i>
          <i class="bi bi-caret-left"></i>
          <div className="entrer" id="et1"></div>
        </div>
        <div className="dec">
          <div className="decor"></div>
          <div className="places">
            <div class="frst">
              <div className="place1"></div>
              <div className="place2"></div>
              <div className="place3"></div>
              <div className="place4"></div>
              <div className="place5"></div>
              <div className="place6"></div>
              <div className="place7"></div>
              <div className="place8"></div>
            </div>
            <div class="scnd">
              <div className="place9"></div>
              <div className="place10"></div>
              <div className="place11"></div>
              <div className="place12"></div>
              <div className="place13"></div>
              <div className="place14"></div>
              <div className="place15"></div>
              <div className="place16"></div>
            </div>
          </div>
          <div className="decor"></div>
        </div>
      </div>
    </div>
  );
}
