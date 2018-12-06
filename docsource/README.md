## CRMint Docs

To generate the CRMint docs:

1.  install [Jekyll](https://jekyllrb.com/):

    ```shell
    $ cd docsource/
    $ gem install bundler
    $ bundle install
    ```

1.  Server the `docs` locally :

  ```shell
    $ cd docsource/
    $ bundle exec jekyll serve
    ```

1.  Build the `docs` directory:

    ```shell
    $ cd docsource/
    $ bundle exec jekyll b -i -d ../docs
    ```

The docs should now be up to date and ready for pushing to GitHub.
