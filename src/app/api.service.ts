import { Injectable } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../environments/environment.development';


@Injectable({
  providedIn: 'root' 
})


export class ApiService {
  private baseUrl = environment.apiUrl; // your API base URL

  constructor(private http: HttpClient) {}

  // Example API call for experiments
  getExperiments(): Promise<{ items: any[] }> {
    return firstValueFrom(this.http.get<{ items: any[] }>(`${this.baseUrl}/experiments/`));
  }

  getExperimentsBasedOnSearch(searchTerm: string): Promise<{ items: any[] }> {
    return firstValueFrom(this.http.get<{ items: any[] }>(`${this.baseUrl}/experiments/`, {
        params: {
          search: searchTerm || ''
        }
      }));
  }

  downloadExperimentResults(experimentId: any): Promise<HttpResponse<Blob>> {
  return firstValueFrom(
    this.http.get(`${this.baseUrl}/experiments/download/${experimentId}`, {
      responseType: 'blob',
      observe: 'response'
    })
  );
}

  downloadExperimentSource(experimentId: any): Promise<HttpResponse<Blob>> {
  return firstValueFrom(
    this.http.get(`${this.baseUrl}/experiments/download/source/${experimentId}`, {
      responseType: 'blob',
      observe: 'response'
    })
  );
}

  resetPassword(payload: any): Promise<{ message?: string }> {
    return firstValueFrom(this.http.put<{ message?: string }>(`${this.baseUrl}/users/password`, payload));
  }

  createExperiment(payload: any): Promise<{
    error?: string; message?: string
}> {
    return firstValueFrom(this.http.post<{ message?: string }>(`${this.baseUrl}/experiments/`, payload));
  }

    eraseExperimentResults(experimentId: any): Promise<{
    error?: string; message?: string
}> {
    return firstValueFrom(this.http.delete<{ message?: string }>(`${this.baseUrl}/experiments/erase/${experimentId}`));
  }

  deleteExperiment(experimentId: any): Promise<{
    error?: string; message?: string
}> {
    return firstValueFrom(this.http.delete<{ message?: string }>(`${this.baseUrl}/experiments/${experimentId}`));
  }

    createUser(payload: any): Promise<{
    error?: string; message?: string
}> {
    return firstValueFrom(this.http.post<{ message?: string }>(`${this.baseUrl}/users/`, payload));
  }

    getUsers(): Promise<{ items: any[] }> {
  return firstValueFrom(this.http.get<{ items: any[] }>(`${this.baseUrl}/users/`));
}

  login(credentials: any): Promise<{
    response: any
}> {
    return firstValueFrom(this.http.post<{ response: any }>(`${this.baseUrl}/users/login`, credentials));
  }


}
