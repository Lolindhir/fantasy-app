import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MarkdownModule } from 'ngx-markdown';
import { SharedMaterialImports } from '../shared/shared-material-imports';

@Component({
  selector: 'app-about',
  imports: [
    MarkdownModule,
    SharedMaterialImports
  ],
  standalone: true,
  templateUrl: './about.html',
  styleUrl: './about.scss'
})

export class AboutComponent implements OnInit {

  markdownText = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get('docs/Salary_Explanation.md', { responseType: 'text' })
      .subscribe(data => {
        this.markdownText = data;
      });
  }

}
