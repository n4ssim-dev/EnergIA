import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class PredictionService {

    private url = "http://localhost:3001/api";

    constructor(private http: HttpClient){};

    getRegions(){
          return this.http.get<any>(`${this.url}/regions`); 

    }
}
