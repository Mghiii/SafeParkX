import React from "react";
import "./park.css"

export default function Park() {
  return (
    <div>
      <div className="titre">
        <h1>Gestion de Parking :</h1>
      </div>
      <div className="parking">
        <div className="ent">
          <div className="entrer"></div>
          <div className="entrer"></div>
        </div>
        <div className="dec">
          <div className="decor"></div>
          <div className="decor"></div>
        </div>
      </div>
    </div>
  );
}
