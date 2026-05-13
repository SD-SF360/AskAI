import React from "react";
import {
 BarChart,
 Bar,
 XAxis,
 YAxis,
 Tooltip,
 ResponsiveContainer,
 CartesianGrid
} from "recharts";

function WicketsChart({data}){

 if(!data || data.length===0) return null;

 return(

  <ResponsiveContainer width="100%" height={320}>

   <BarChart data={data}>

    <CartesianGrid strokeDasharray="3 3"/>

   <XAxis dataKey="player"/>

    <YAxis/>

    <Tooltip/>

    <Bar
     dataKey="value"
     fill="#f97316"
    />

   </BarChart>

  </ResponsiveContainer>

 );

}

export default WicketsChart;