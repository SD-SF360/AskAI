import React from "react";
import { useParams } from "react-router-dom";

function ProfilePage(){

  const { type, name } = useParams();

  return(
    <div className="profilePage">

      <div className="profileCard">

        <img
          src="https://via.placeholder.com/120"
          alt="dp"
          className="profileDP"
        />

        <h2>{name.toUpperCase()}</h2>
        <p className="profileType">{type.toUpperCase()}</p>

        <div className="comingSoon">
          🚧 Coming Soon
        </div>

      </div>

    </div>
  )
}

export default ProfilePage;