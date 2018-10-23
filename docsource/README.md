## CRMint Docs

To generate the CRMint docs:

1.  install [Jekyll](https://jekyllrb.com/):

    ```shell
    gem install bundler jekyll
    ```

1.  Build the `docs` directory:

    ```shell
    cd docsource/
    jekyll b -i -d ../docs
    ```

The docs should now be up to date and ready for pushing to GitHub.
