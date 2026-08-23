# AutomationML Learning Path

These notebooks are executable lessons built against the SDK's public API.
Run them in order:

1. `01_build-a-drive-station.ipynb` develops a motor and power-supply scenario
   from concrete instances to links and stable class semantics.
2. `02_json-and-xml-exchange.ipynb` gives JSON and XML serialization its own
   focused lesson and proves that both formats reconstruct the same model.
3. `03_inheritance-interfaces-and-validation.ipynb` investigates class
   inheritance and interface warnings, repairs a robot-cell instance, and adds
   a valid InternalLink.

## Start locally

From the repository root:

```bash
python -m pip install -e ".[learning]"
jupyter lab learning
```

Open the first notebook and use **Run All Cells**. Each lesson includes
prediction prompts, executable checks, and optional exercises. The committed
notebooks start without stored outputs so every learner produces the results
locally.
