import React from "react";
import {
 BarChart,
 Bar,
 XAxis,
 YAxis,
 Tooltip,
 ResponsiveContainer
} from "recharts";

function DynamicChart({data}){

 if(!data) return null;

 return(

  <ResponsiveContainer width="100%" height={350}>

   <BarChart data={data}>

    <XAxis dataKey="name"/>

    <YAxis/>

    <Tooltip/>

    <Bar dataKey="value" fill="#38bdf8"/>

   </BarChart>

  </ResponsiveContainer>

 );

}

export default DynamicChart;