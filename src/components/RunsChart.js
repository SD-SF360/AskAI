import React from "react";
import {
 LineChart,
 Line,
 XAxis,
 YAxis,
 Tooltip,
 ResponsiveContainer,
 CartesianGrid
} from "recharts";

function RunsChart({data}){

 if(!data || data.length===0) return null;

 return(

  <ResponsiveContainer width="100%" height={320}>

   <LineChart data={data}>

    <CartesianGrid strokeDasharray="3 3" />

    <XAxis dataKey="player"/>

    <YAxis/>

    <Tooltip/>

    <Line
     type="monotone"
     dataKey="value"
     stroke="#38bdf8"
     strokeWidth={3}
    />

   </LineChart>

  </ResponsiveContainer>

 );

}

export default RunsChart;