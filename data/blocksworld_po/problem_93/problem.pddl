(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable purple)
		(on red purple)
		(on blue red)
		(on orange blue)
		(clear orange)
		(ontable yellow)
		(clear yellow)

		(ontable green)
		(clear green)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(on purple orange)
		(clear purple)
		(ontable green)
		(on red green)
		(clear red)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
	))
)