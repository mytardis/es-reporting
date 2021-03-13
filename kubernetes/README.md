## Kubernetes deployment

1. Start with changing configMap values in `configmap.yaml` file according to your setup (namespaces, names, credentials).

    Deploy config map:
   `kubectl create -f configmap.yaml`


2. Run initial job to build index and populate data.

    `kubectl create -f job-create.yaml`

    It will provide script with 2 optional arguments, --days=-1 to index all data and --rebuild to create index in Elasticsearch.

3. Schedule cron job to update only last 24 hours of data.

    `kubectl create -f cronjob-update.yaml`

### Kibana

You can deploy Kibana:

`kubectl create -f kibana.yaml`

and expose it to the public using (nginx) Ingress with username/password authentication.

Firstly, generate auth file and load it as a secret:

```
htpasswd -c auth.txt mytardis
kubectl -n mytardis create secret generic reporting --from-file=auth.txt
rm auth.txt
```

Secondly, deploy ingress with annotation to use secret:

`kubectl create -f ingress.yaml`

### Vouch

Vouch proxy will allow you to restrict access to Kibana instance using number of oAuth providers, like Google, Okta, etc.

`helm repo add halkeye https://halkeye.github.io/helm-charts/`

`helm install halkeye/vouch --version 0.2.1 -f vouch.yaml --namespace ingress-nginx --name vouch`

`helm del --purge vouch`
