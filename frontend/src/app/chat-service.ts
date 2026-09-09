import { HttpClient } from '@angular/common/http';
import { Injectable, Service, signal } from '@angular/core';
import { Router } from '@angular/router';


@Injectable({ providedIn: 'root' })
export class ChatService {

    //private url = "http://localhost:3001/api/normaliser"; 
      private url = "http://energia-gateway:3000/api/normaliser";

    constructor(private http: HttpClient, private router: Router) { };
    messages = signal([
        {
            auteur: 'bot',
            texte: 'Bonjour, comment puis-je vous aider aujourd\'hui ?',
            loading: false
        }

    ]);


    assistance(question: string) {

        // Ajouter la question utilisateur
        this.messages.update(messages => [
            ...messages,
            {
                auteur: "user",
                texte: question,
                loading: false
            }
        ]);

        // Ajouter un message temporaire du bot
        this.messages.update(messages => [
            ...messages,
            {
                auteur: "bot",
                texte: "",
                loading: true
            }
        ]);

        this.http.get<any>(
            this.url,
             {
                params: { question }
             }
        )
        .subscribe({

        next: result => {


        // Remplacer le loader par la vraie réponse
        this.messages.update(messages => {

        const newMessages = [...messages];


        const index = newMessages.findIndex(
        message => message.loading === true
        );


        if (index !== -1) {
            
        newMessages[index] = {
        auteur: "bot",
        texte: result.reponse.reponse,
        loading: false
         };
        }
        return newMessages;
        });
        },


        error: err => {

        this.messages.update(messages => {
        const newMessages = [...messages];

        const index = newMessages.findIndex(
        message => message.loading === true
        );

        if (index !== -1) {

        newMessages[index] = {
        auteur: "bot",
        texte: "Erreur serveur",
        loading: false
        };

        }
        return newMessages;
        });
        }
        });
    }
}
