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
		(ontable orange)
		(clear orange)
		(ontable blue)
		(on green blue)
		(clear green)

		(ontable purple)
		(on red purple)
		(on yellow red)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable green)
		(clear green)
		(ontable yellow)
		(on purple yellow)
		(clear purple)

		(ontable orange)
		(clear orange)
		(ontable red)
		(on blue red)
		(clear blue)
	))
)