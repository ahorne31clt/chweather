export const LEVEL2={
 REF:{label:'Reflectivity',key:'reflect',unit:'dBZ',min:-10,max:80,stops:[[-10,'#536773'],[0,'#2768a4'],[10,'#36a4bb'],[20,'#40ad54'],[30,'#c7cd43'],[40,'#edac34'],[50,'#df493d'],[60,'#ae2c70'],[70,'#df9cd7'],[80,'#ffffff']]},
 VEL:{label:'Radial velocity',key:'velocity',unit:'kt',min:-100,max:100,convert:1.94384449,stops:[[-100,'#78e9db'],[-60,'#2dce72'],[-20,'#218c52'],[0,'#8c9890'],[20,'#a64746'],[60,'#f35a59'],[100,'#ffd1d1']]},
 RHO:{label:'Correlation coefficient (CC)',key:'rho',unit:'ratio',min:.2,max:1.05,stops:[[.2,'#b55866'],[.6,'#dc874a'],[.8,'#e1d15d'],[.9,'#70b46c'],[.95,'#459fbb'],[.98,'#626fbc'],[1.05,'#af82bd']]},
 ZDR:{label:'Differential reflectivity (ZDR)',key:'zdr',unit:'dB',min:-2,max:6,stops:[[-2,'#585bad'],[-1,'#5ba3be'],[0,'#72b690'],[1,'#c2c77c'],[2,'#dfb659'],[4,'#d26754'],[6,'#ba78b5']]},
 PHI:{label:'Differential phase (ΦDP)',key:'phi',unit:'°',min:0,max:360,stops:[[0,'#8c62b0'],[60,'#527eb6'],[120,'#53a4a4'],[180,'#84b669'],[240,'#d6c363'],[300,'#d67753'],[360,'#b3679b']]},
 SW:{label:'Spectrum width',key:'spectrum',unit:'kt',min:0,max:40,convert:1.94384449,stops:[[0,'#263e3b'],[5,'#548d7a'],[10,'#a2bc78'],[20,'#d7b362'],[30,'#cf7b53'],[40,'#a669a5']]}
};
export const MRMS={
 composite:{label:'QC composite reflectivity',folder:'MergedReflectivityQCComposite_00.50',category:10,parameter:0,unit:'dBZ',min:-10,max:80,stops:LEVEL2.REF.stops},
 rate:{label:'Radar precipitation rate',folder:'PrecipRate_00.00',category:6,parameter:1,unit:'in/hr',convert:1/25.4,min:0,max:4,stops:[[0,'#263e3b'],[.05,'#478a65'],[.25,'#96bd72'],[.5,'#d2bd62'],[1,'#d88d4b'],[2,'#cf535f'],[4,'#a278b8']]},
 qpe1:{label:'Radar-only accumulation / 1 hour',folder:'RadarOnly_QPE_01H_00.00',category:6,parameter:2,hours:1,unit:'in',min:0,max:6},
 qpe3:{label:'Radar-only accumulation / 3 hours',folder:'RadarOnly_QPE_03H_00.00',category:6,parameter:3,hours:3,unit:'in',min:0,max:6},
 qpe6:{label:'Radar-only accumulation / 6 hours',folder:'RadarOnly_QPE_06H_00.00',category:6,parameter:4,hours:6,unit:'in',min:0,max:6},
 qpe24:{label:'Radar-only accumulation / 24 hours',folder:'RadarOnly_QPE_24H_00.00',category:6,parameter:6,hours:24,unit:'in',min:0,max:6}
};
for(const p of Object.values(MRMS))if(p.hours){p.convert=1/25.4;p.stops=[[0,'#263e3b'],[.1,'#477b76'],[.25,'#4eae76'],[.5,'#a3bd72'],[1,'#d6c05e'],[2,'#d68c4e'],[3,'#d35a64'],[6,'#aa83bc']];}
export function palette(spec){
 const colors=spec.stops.map(([value,hex])=>[value,[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16))]);
 return value=>{if(!Number.isFinite(value))return [0,0,0,0];let index=0;while(index<colors.length-2&&value>colors[index+1][0])index++;
  const [a,ca]=colors[index],[b,cb]=colors[index+1],f=Math.max(0,Math.min(1,(value-a)/(b-a)));return [...ca.map((c,i)=>Math.round(c+(cb[i]-c)*f)),value<spec.min?0:255];};
}
