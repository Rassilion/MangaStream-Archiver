# MangaStream Archiver
Python bot for downloading new releases from MangaStream

- data is in sqllite database
- get manga list from site
- get chapters from manga list

## Database model

##### Manga

- name
- url
- chapters <- Chapter


##### Chapter

- name
- url
- cdn_id 
- manga -> Manga

 



